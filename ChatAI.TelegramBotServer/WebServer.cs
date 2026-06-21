using ChatAI.Shared;
using ChatAI.TelegramBotServer.Components;
using Microsoft.FluentUI.AspNetCore.Components;
using Blazored.LocalStorage;

namespace ChatAI.TelegramBotServer;

public class WebServer
{
    public async Task RunAsync(string[] args, AgentClient agentClient, CancellationToken cancellationToken = default)
    {
        var builder = WebApplication.CreateBuilder(args);

        // Add services to the container.
        builder.Services.AddRazorComponents()
                .AddInteractiveServerComponents();

        builder.WebHost.UseUrls("http://0.0.0.0:55434");
        builder.Services.AddSingleton(agentClient);
        builder.Services.AddFluentUIComponents();
        builder.Services.AddBlazoredLocalStorage();

        var app = builder.Build();

        // Configure the HTTP request pipeline.
        if (!app.Environment.IsDevelopment())
        {
            app.UseExceptionHandler("/Error");
        }

        app.UseStaticFiles();
        app.UseAntiforgery();

        app.MapRazorComponents<App>()
            .AddInteractiveServerRenderMode();

        await app.RunAsync();
    }
}
