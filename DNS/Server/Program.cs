using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text;
using System.Threading.Tasks;
using System.Timers;
using DNS.Protocol;
using DNS.Server;

/*
* 00020100000100000000000004757266750272750000010001
*/

namespace Server
{
    internal class Program
    {
        public static readonly ConcurrentDictionary<Query, List<Query>> Cache; // первое dns - имя, второе - IpV4 адрес

        private static IPEndPoint forwarder;
        private static UdpClient dnsPort;
        private static readonly Timer Timer;

        private static Random rnd;
        // public static readonly ConcurrentDictionary<Query, Query> NsToIpV6; // первое dns - имя, второе - IpV6 адрес
        // public static readonly ConcurrentDictionary<Query, Query> NsToNs; // первое dns - имя, второе -  ns запись

        static Program()
        {
            Cache = new ConcurrentDictionary<Query, List<Query>>();
            Timer = new Timer(1000);
            Timer.Elapsed += (sender, args) =>
            {
                foreach (var query in Cache.Keys)
                {
                    foreach (var q in Cache[query]) q.TTL--;
                    Cache[query] = Cache[query].Where(x => x.TTL != 0).ToList();
                    if (Cache[query].Count != 0) continue;
                    Cache.TryRemove(query, out _);
                }
            };
        }

        public static void Main(string[] args)
        {
            forwarder = new IPEndPoint(new IPAddress(new byte[] { 8, 8, 8, 8 }), 53);
            var exit = false;
            var port = 53;
            for(var i = 0;i < args.Length;i++)
            {
                var p = args[i];
                switch (p)
                {
                    case "-p":
                    case "--port":
                        port = int.Parse(args[i + 1]);
                        break;
                    case "-f":
                    case "--forwarder":
                        forwarder.Address = IPAddress.Parse(args[i + 1]);
                        break;
                    case "-h":
                    case "--help":
                        Console.WriteLine("Программа запускает кэширующий dns сервер. По-умолчанию сервер запускается на стандартном 53 порту и обращатсяк к срвру по ip 8.8.8.8" +
                                          "-p, --port - какой порт прослушивать." +
                                          "-f, --forwarder - К какому срвру обращаться с запросом информации" +
                                          "-h, --help - вывести данное сообщение");
                        exit = true;
                        break;
                }
            }
            Timer.Start();
            rnd = new Random();
            if(!exit) Serverwork(port);
        }

        private static void Serverwork(int port)
        {
            dnsPort = new UdpClient(port);
            Console.WriteLine("Я слушаю");
            try
            {
                while (true)
                {
                    IPEndPoint ip = null;
                    var data = dnsPort.Receive(ref ip);
                    var x = RequestProcessing(data, ip);
                    Task.Run(x);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex.Message);
            }
            // ReSharper disable once FunctionNeverReturns
        }

        private static Action RequestProcessing(IReadOnlyList<byte> data, IPEndPoint ip)
        {
            var f = new Action(() =>
            {
                var package = new DnsPackage(data);
                var answer = new DnsPackage(package.Header.Opcode)
                {
                    Header =
                    {
                        Id = package.Header.Id,
                        Qr = true,
                        RecursionDesired = package.Header.RecursionDesired
                    }
                };
                foreach (var query in package.QuestionQueries)
                {
                    answer.QuestionQueries.Add(query);
                    if (query.Type == Query.QueryType.Error)
                    {
                        Console.WriteLine("Я не работаю с данным типом пакетов");
                        answer.Header.RCode = 4;
                        break;
                    }

                    if (Cache.ContainsKey(query))
                    {
                        answer.NonAuthorityAnswer = Cache[query];
                        Console.WriteLine($"{ip} {query.Type.ToString()} {query.Name} cache");
                    }
                    else
                    {
                        Console.WriteLine($"{ip} {query.Type.ToString()} {query.Name} forwarder");
                        var question = new DnsPackage(0)
                        {
                            Header =
                            {
                                Qr = false,
                                RecursionDesired = true
                            }
                        };
                        question.QuestionQueries.Add(query);
                        var dgram = question.ConvertPackageToByte();
                        var client = new UdpClient(rnd.Next() % 65000);
                        client.Send(dgram, dgram.Length, forwarder);
                        dgram = client.Receive(ref forwarder);
                        var forwarderAnswer = new DnsPackage(dgram);
                        foreach (var answerQuery in forwarderAnswer.NonAuthorityAnswer)
                        {
                            answer.NonAuthorityAnswer.Add(answerQuery);
                            if (!Cache.ContainsKey(query)) Cache[query] = new List<Query>();
                            Cache[query].Add(answerQuery);
                        }

                        foreach (var answerQuery in forwarderAnswer.AuthorityAnswer)
                        {
                            answer.NonAuthorityAnswer.Add(answerQuery);
                            if (!Cache.ContainsKey(query)) Cache[query] = new List<Query>();
                            Cache[query].Add(answerQuery);
                        }

                        foreach (var answerQuery in forwarderAnswer.Additional)
                        {
                            answer.NonAuthorityAnswer.Add(answerQuery);
                            if (!Cache.ContainsKey(query)) Cache[query] = new List<Query>();
                            Cache[query].Add(answerQuery);
                        }
                    }
                }
                var answerDGram = answer.ConvertPackageToByte();
                dnsPort.SendAsync(answerDGram, answerDGram.Length, ip);
            });
            return f;
        }
    }
}