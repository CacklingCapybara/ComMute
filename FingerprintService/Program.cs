using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using SoundFingerprinting;
using SoundFingerprinting.Audio;
using SoundFingerprinting.Builder;
using SoundFingerprinting.InMemory;
using SoundFingerprinting.Data;
using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Collections.Generic;

var builder = WebApplication.CreateBuilder(args);

// Configure services
builder.Services.AddSingleton<IModelService>(new InMemoryModelService());
builder.Services.AddSingleton<IAudioService>(new SoundFingerprintingAudioService());

var app = builder.Build();

var modelService = app.Services.GetRequiredService<IModelService>();
var audioService = app.Services.GetRequiredService<IAudioService>();

// Keep track of fingerprinted items manually since InMemoryModelService doesn't expose tracks list
var trackRegistry = new Dictionary<string, (string Title, string Artist)>();

// Health check endpoint
app.MapGet("/health", () => Results.Ok(new { status = "healthy", service = "fingerprint" }));

// Fingerprint a commercial (store in database)
app.MapPost("/fingerprint", async (HttpRequest request) =>
{
    try
    {
        if (!request.Form.Files.Any())
        {
            return Results.BadRequest(new { error = "No audio file provided" });
        }

        var file = request.Form.Files[0];
        var name = request.Form["name"].ToString();

        if (string.IsNullOrEmpty(name))
        {
            return Results.BadRequest(new { error = "Commercial name is required" });
        }

        // Save file temporarily
        var tempPath = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString() + Path.GetExtension(file.FileName));
        using (var stream = new FileStream(tempPath, FileMode.Create))
        {
            await file.CopyToAsync(stream);
        }

        try
        {
            // Create track info
            var trackId = Guid.NewGuid().ToString();
            var track = new TrackInfo(trackId, name, "Commercial");

            // Generate fingerprints
            var avHashes = await FingerprintCommandBuilder.Instance
                .BuildFingerprintCommand()
                .From(tempPath)
                .UsingServices(audioService)
                .Hash();

            // Store in database
            modelService.Insert(track, avHashes);
            
            // Store in our registry
            trackRegistry[trackId] = (name, "Commercial");

            return Results.Ok(new
            {
                success = true,
                name = name,
                trackId = trackId,
                hashesCount = avHashes.Audio?.Count ?? 0
            });
        }
        finally
        {
            // Clean up temp file
            if (File.Exists(tempPath))
            {
                File.Delete(tempPath);
            }
        }
    }
    catch (Exception ex)
    {
        return Results.Problem(
            detail: ex.Message,
            statusCode: 500,
            title: "Fingerprinting failed"
        );
    }
});

// Query/match audio against database
app.MapPost("/query", async (HttpRequest request) =>
{
    try
    {
        if (!request.Form.Files.Any())
        {
            return Results.BadRequest(new { error = "No audio file provided" });
        }

        var file = request.Form.Files[0];
        var secondsToAnalyze = 10;

        if (request.Form.ContainsKey("seconds"))
        {
            int.TryParse(request.Form["seconds"], out secondsToAnalyze);
        }

        // Save file temporarily
        var tempPath = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString() + Path.GetExtension(file.FileName));
        using (var stream = new FileStream(tempPath, FileMode.Create))
        {
            await file.CopyToAsync(stream);
        }

        try
        {
            // Query the database
            var queryResult = await QueryCommandBuilder.Instance
                .BuildQueryCommand()
                .From(tempPath, secondsToAnalyze, 0)
                .UsingServices(modelService, audioService)
                .Query();

            // Check if we have matches
            if (queryResult.ContainsMatches && queryResult.BestMatch != null)
            {
                var bestMatch = queryResult.BestMatch;
                
                return Results.Ok(new
                {
                    match = true,
                    name = bestMatch.Track.Title,
                    trackId = bestMatch.Track.Id,
                    confidence = bestMatch.Score,
                    matchedAt = bestMatch.TrackMatchStartsAt,
                    queryLength = bestMatch.QueryLength,
                    coverageLength = bestMatch.TrackCoverageWithPermittedGapsLength
                });
            }
            else
            {
                return Results.Ok(new
                {
                    match = false,
                    confidence = 0.0
                });
            }
        }
        finally
        {
            // Clean up temp file
            if (File.Exists(tempPath))
            {
                File.Delete(tempPath);
            }
        }
    }
    catch (Exception ex)
    {
        return Results.Problem(
            detail: ex.Message,
            statusCode: 500,
            title: "Query failed"
        );
    }
});

// List all fingerprinted commercials
app.MapGet("/commercials", () =>
{
    try
    {
        var commercials = trackRegistry.Select(kvp => new
        {
            id = kvp.Key,
            name = kvp.Value.Title,
            artist = kvp.Value.Artist
        }).ToList();

        return Results.Ok(new
        {
            count = commercials.Count,
            commercials = commercials
        });
    }
    catch (Exception ex)
    {
        return Results.Problem(
            detail: ex.Message,
            statusCode: 500,
            title: "Failed to list commercials"
        );
    }
});

// Delete a commercial from database
app.MapDelete("/commercial/{trackId}", (string trackId) =>
{
    try
    {
        if (!trackRegistry.ContainsKey(trackId))
        {
            return Results.NotFound(new { error = "Commercial not found" });
        }

        // Note: InMemoryModelService doesn't have a delete method
        // In production, use a persistent storage like Emy
        return Results.Ok(new
        {
            message = "Delete not implemented with InMemoryModelService",
            note = "Restart service to clear all fingerprints"
        });
    }
    catch (Exception ex)
    {
        return Results.Problem(
            detail: ex.Message,
            statusCode: 500,
            title: "Delete failed"
        );
    }
});

// Get statistics
app.MapGet("/stats", () =>
{
    try
    {
        return Results.Ok(new
        {
            totalCommercials = trackRegistry.Count,
            service = "SoundFingerprinting",
            version = "12.6.0",
            storage = "InMemory"
        });
    }
    catch (Exception ex)
    {
        return Results.Problem(
            detail: ex.Message,
            statusCode: 500,
            title: "Failed to get stats"
        );
    }
});

app.Run("http://0.0.0.0:5000");