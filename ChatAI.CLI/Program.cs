using ChatAI.Shared;
using System.Reflection;
using System.Text.Json;

namespace ChatAI.CLI;

internal class Program
{
    static async Task Main(string[] args)
    {
        Console.Write("ChatAI");
        Console.InputEncoding = System.Text.Encoding.Unicode;
        Console.OutputEncoding = System.Text.Encoding.Unicode;
        Console.ResetColor();
        AgentClient.User.BinPath = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? AppContext.BaseDirectory;
        var settings = JsonSerializer.Deserialize<AgentSettings>(File.ReadAllText(Path.Join(AgentClient.User.BinPath,"appsettings.json")));

        if(settings is null)
        {
            Console.WriteLine("appsettings.json not found");
            return;
        }

        var agentClient = new AgentClient(settings.ApiKey, settings.Url);
        var user = new AgentClient.User
        {
            Model = settings.Model,
            Instruction = settings.Instruction
        };
        var agent = AgentClient.GetAIAgentForUser(agentClient.Client, user);
        var session = await agent.CreateSessionAsync();
        var input = string.Empty;

        while(true)
        {
            Console.WriteLine("\n\n---");
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.Write(" > ");
            input = Console.ReadLine();
            if (string.IsNullOrWhiteSpace(input))
            {
                Console.ResetColor();
                continue;
            }
            else if (input == "exit")
            {
                Console.ResetColor();
                return;
            }
            Console.ResetColor();
            Console.WriteLine("---\n\nThinking...\n");
            Console.ForegroundColor = ConsoleColor.Yellow;

            await foreach(var chunk in agent.RunStreamingAsync(input, session))
                Console.Write(chunk);

            Console.ResetColor();
        }
    }
}
