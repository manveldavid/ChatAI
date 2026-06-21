using ChatAI.Shared;
using Microsoft.Extensions.AI;
using System.Text;
using Telegram.Bot;
using Telegram.Bot.Types;
using Telegram.Bot.Types.Enums;

namespace ChatAI.TelegramBotServer;

public class TelegramBot
{
    public static class Command
    {
        public const string Start = "/start";
        public const string Clear = "/clear";
        public const string SetModel = "/setmodel";
        public const string Instruction = "/instruction";
        public const string Id = "/id";

        public static string[] Commands = [Start, Clear, SetModel, Instruction, Id];
    }
    public async Task RunAsync(AgentClient agentClient, string apiKey, TimeSpan pollPeriod, CancellationToken cancellationToken)
    {
        if (string.IsNullOrEmpty(apiKey))
            return;

        var offset = 0;
        var telegramBot = new TelegramBotClient(apiKey);

        while (!cancellationToken.IsCancellationRequested)
        {
            await Task.Delay(pollPeriod, cancellationToken);

            var updates = Array.Empty<Update>();
            try
            {
                updates = await telegramBot.GetUpdates(offset, timeout: (int)pollPeriod.TotalSeconds, cancellationToken: cancellationToken);
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex.ToString());
            }

            if (!cancellationToken.IsCancellationRequested)
            {
                foreach (var update in updates)
                {
                    offset = update.Id + 1;

                    try
                    {
                        if (update is null || update.Message is null)
                            return;

                        var chatId = update.Message.Chat.Id;
                        var user = agentClient.Users.TryGetValue(chatId, out var savedUser) ? savedUser : new();

                        if (savedUser is null)
                            agentClient.Users.Add(chatId, user);

                        TgMediaFile? tgMedia = null;

                        if (update.Message.VideoNote is not null)
                        {
                            tgMedia = new();
                            tgMedia.File = await telegramBot.GetInfoAndDownloadFile(update.Message.VideoNote.FileId, tgMedia.MemoryStream);
                        }
                        if (update.Message.Voice is not null)
                        {
                            tgMedia = new();
                            tgMedia.File = await telegramBot.GetInfoAndDownloadFile(update.Message.Voice.FileId, tgMedia.MemoryStream);
                        }
                        if (update.Message.Photo is not null)
                        {
                            tgMedia = new();
                            tgMedia.File = await telegramBot.GetInfoAndDownloadFile(update.Message.Photo.Last().FileId, tgMedia.MemoryStream);
                        }
                        if (update.Message.Video is not null)
                        {
                            tgMedia = new();
                            tgMedia.File = await telegramBot.GetInfoAndDownloadFile(update.Message.Video.FileId, tgMedia.MemoryStream);
                        }
                        if (update.Message.Audio is not null)
                        {
                            tgMedia = new();
                            tgMedia.File = await telegramBot.GetInfoAndDownloadFile(update.Message.Audio.FileId, tgMedia.MemoryStream);
                        }
                        if (update.Message.Document is not null)
                        {
                            tgMedia = new();
                            tgMedia.File = await telegramBot.GetInfoAndDownloadFile(update.Message.Document.FileId, tgMedia.MemoryStream);
                        }

                        if (tgMedia is not null)
                        {
                            tgMedia.MemoryStream.Position = 0;
                            await user.History.AddAdditionAsync(tgMedia.MemoryStream, tgMedia.File.FilePath ?? string.Empty);
                            await tgMedia.MemoryStream.DisposeAsync();
                        }

                        if(update.Message.Caption is not null)
                            update.Message.Text = update.Message.Caption;

                        if (update.Message.Text is null)
                            continue;

                        var messageText = update.Message.Text;
                        var agent = AgentClient.GetAIAgentForUser(agentClient.Client, user);

                        if (user.History.Session is null)
                            user.History.Session = await agent.CreateSessionAsync();

                        if(Command.Commands.Any(c => messageText.StartsWith(c)))
                        {
                            if (messageText.StartsWith(Command.Id))
                            {
                                await telegramBot.SendMessage(chatId, chatId.ToString(), cancellationToken: cancellationToken);
                            }
                            else if (messageText.StartsWith(Command.SetModel))
                            {
                                var setModel = messageText.Replace(Command.SetModel, "").Trim();
                                user.Model = setModel;
                            }
                            else if (messageText.StartsWith(Command.Instruction))
                            {
                                var instruction = messageText.Replace(Command.Instruction, "").Trim();
                                user.Instruction = instruction;
                            }
                            else if (messageText.StartsWith(Command.Clear))
                            {
                                user.History.Session = null;
                                user.IsThinking = false;
                                user.History.Messages.Clear();
                                user.History.Additions.Clear();
                            }

                            continue;
                        }

                        var sb = new StringBuilder();
                        var chatActionDelay = Task.CompletedTask;
                        var textDelay = Task.CompletedTask;
                        var messageSended = 0;
                        var lastSendedMessage = new Message();
                        var charLimit = 4090;
                        var lastText = string.Empty;
                        var response = string.Empty;

                        Func<ParseMode, string, string, Task<Message>> sendMessage =
                            async (ParseMode parseMode, string sended, string response) =>
                            {
                                var needNewMessage = (lastText.Length / charLimit) + 1 < (response.Length / charLimit) + 1;
                                var messageRemains = response.Substring((response.Length / charLimit) * charLimit);
                                if (needNewMessage || messageSended == 0)
                                {
                                    if (messageSended > 0)
                                    {
                                        var lastEdit = response.Substring(((response.Length / charLimit) - 1) * charLimit, charLimit);

                                        if (lastEdit != lastText)
                                            await telegramBot.EditMessageText(chatId, lastSendedMessage.Id, lastEdit, parseMode, cancellationToken: cancellationToken);
                                    }

                                    messageSended++;
                                    return await telegramBot.SendMessage(chatId, messageRemains, parseMode, cancellationToken: cancellationToken);
                                }
                                else if (response != lastText)
                                    return await telegramBot.EditMessageText(chatId, lastSendedMessage.Id, messageRemains, parseMode, cancellationToken: cancellationToken);

                                return lastSendedMessage;
                            };

                        var newMessage = new AppChatMessage() { Content = messageText, Role = ChatRole.User };
                        user.History.Messages.Add(newMessage);

                        var contents = new List<AIContent>() { new TextContent(newMessage.Content) };

                        foreach (var data in user.History.Additions)
                            contents.Add(new DataContent(data.Data, data.MediaType));

                        await foreach (var chunk in agent.RunStreamingAsync(new ChatMessage() { Contents = contents }, user.History.Session))
                        {
                            var textChunk = chunk.ToString();
                            sb.Append(textChunk);

                            if (textDelay.IsCompleted)
                            {
                                textDelay = Task.Delay(500);

                                response = sb.ToString();

                                if (string.IsNullOrEmpty(textChunk))
                                    user.IsThinking = true;
                                else if(user.IsThinking)
                                    user.IsThinking = false;

                                if(user.IsThinking)
                                    response += "\n\nThinking ...";

                                try
                                {
                                    lastSendedMessage = await sendMessage(ParseMode.Markdown, lastText, response);
                                }
                                catch
                                {
                                    lastSendedMessage = await sendMessage(ParseMode.None, lastText, response);
                                }

                                lastText = response;
                            }
                            if (chatActionDelay.IsCompleted)
                            {
                                chatActionDelay = Task.Delay(3000);
                                await telegramBot.SendChatAction(chatId, ChatAction.Typing);
                            }
                        }

                        response = sb.ToString();
                        user.IsThinking = false;
                        if (lastText!= response)
                        {
                            try
                            {
                                await sendMessage(ParseMode.Markdown, lastText, response);
                            }
                            catch
                            {
                                await sendMessage(ParseMode.None, lastText, response);
                            }
                        }

                        user.History.Additions.Clear();
                        user.History.Messages.Add(new()
                        {
                            Content = response,
                            Role = ChatRole.Assistant
                        });
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine(ex.ToString());
                    }
                }
            }
        }
    }
}