using Microsoft.Agents.AI;
using Microsoft.AspNetCore.StaticFiles;
using Microsoft.Extensions.AI;
using OpenAI;
using OpenAI.Chat;
using System;
using System.ClientModel;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;

namespace ChatAI.Shared
{
    public class AgentClient
    {
        public class User
        {
            public static string BinPath { get; set; } = AppContext.BaseDirectory;
            public static string SkillDirectory => Path.Combine(BinPath, "agent", "skills");
            public string Model { get; set; } = "qwen/qwen3.7-plus";
            public string Instruction { get; set; } = string.Empty;
            public bool IsThinking { get; set; }
            public History History { get; set; } = new History();
        }
        public class History
        {
            public List<AppChatMessage> Messages { get; set; } = new List<AppChatMessage>();
            public List<DataContent> Additions { get; set; } = new List<DataContent>();
            public AgentSession Session { get; set; } = null;
            public async Task AddAdditionAsync(Stream stream, string filename)
            {
                using (var ms = new MemoryStream())
                {
                    await stream.CopyToAsync(ms);
                    await Task.Run(() =>
                        Additions.Add(new DataContent(
                            ms.ToArray(),
                            GetMimeType(filename))));
                }
            }
        }
        public Dictionary<long, User> Users { get; set; } = new Dictionary<long, User>();
        public OpenAIClient Client { get; }
    
        public AgentClient(string providerApiKey, string providerUrl)
        {
            Client = new OpenAIClient(
                new ApiKeyCredential(providerApiKey), 
                new OpenAIClientOptions() 
                { 
                    Endpoint = new Uri(providerUrl) 
                });
        }
        public static AIAgent GetAIAgentForUser(OpenAIClient client, User user)
        {
            if (!Directory.Exists(User.SkillDirectory))
                Directory.CreateDirectory(User.SkillDirectory);

            var preInstruction = $"IMPORTANT! -> your skill directory: '{User.SkillDirectory}'.\nIMPORTANT! -> your working directory: '{Directory.GetCurrentDirectory()}'.\nIMPORTANT! -> 'run_skill_script' tool is prohibited then use 'RunPythonScript' tool instead.\n\n";

            var agentOptions = new ChatClientAgentOptions()
            {
                ChatOptions = new ChatOptions()
                {
                    Tools = new List<AITool>()
                    {
                        AIFunctionFactory.Create((Func<string,int,string>)PythonRunner.RunPythonCode),
                        AIFunctionFactory.Create((Func<string,string[],int,string>)PythonRunner.RunPythonScript),
                        AIFunctionFactory.Create((Func<string[],int,string>)PythonRunner.RunPython),
                    },
                    Instructions = preInstruction
                },
                AIContextProviders = new List<AIContextProvider>()
                {
#pragma warning disable MAAI001 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
                    new AgentSkillsProvider(User.SkillDirectory)
#pragma warning restore MAAI001 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
                }
            };

            if (!string.IsNullOrEmpty(user.Instruction))
            {
                agentOptions.ChatOptions.Instructions += user.Instruction;
            }

            var model = user.Model;

            return client
                .GetChatClient(model)
                .AsAIAgent(agentOptions);
        }
        public static string GetMimeType(string filename) 
        {
            if (!new FileExtensionContentTypeProvider()
                .TryGetContentType(filename, out var contentType))
                contentType = "application/octet-stream";

            return contentType;
        }
    }
}

