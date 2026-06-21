using ChatAI.Shared;

namespace ChatAI.TelegramBotServer;

public class Program
{
    public static async Task Main(string[] args)
    {
        var tgBotPollPeriodInSeconds = TimeSpan.FromSeconds(double.TryParse(Environment.GetEnvironmentVariable("TG_BOT_POLL_PERIOD_SECONDS"), out var _tgBotPollPeriodInSeconds) ? _tgBotPollPeriodInSeconds : 10d);
        var apiKey = Environment.GetEnvironmentVariable("API_KEY")!;
        var providerApiKey = Environment.GetEnvironmentVariable("AI_PROVIDER_API_KEY")!;
        var providerUrl = Environment.GetEnvironmentVariable("AI_PROVIDER_URL")!;

        Console.WriteLine("bot run!");

        var agentClient = new AgentClient(providerApiKey, providerUrl);

        await Task.WhenAll(
            [
                new WebServer().RunAsync(
                    args,
                    agentClient,
                    CancellationToken.None),

                new TelegramBot().RunAsync(
                    agentClient,
                    apiKey,
                    tgBotPollPeriodInSeconds,
                    CancellationToken.None),

                new AutonomousTaskDriver().RunAsync(
                    agentClient,
                    CancellationToken.None)
            ]);
    }
}
