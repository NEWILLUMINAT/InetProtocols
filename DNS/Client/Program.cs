using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Runtime.Remoting;
using Server;

namespace Client
{
    internal class Program
    {
        public static void Main(string[] args)
        {
            var x = new DnsPackage(0);
            var rnd = new Random();
            var header = new Header
            {
                Id = rnd.Next(),
                Qr = false,
                Opcode = 0,
                QuestionCount = 1
            };
            x.Header = header;
            var first = new Query
            {
                Name = "vk.com",
                Type = Query.QueryType.Ns
            };
            x.QuestionQueries.Add(first);
            var data = x.ConvertPackageToByte();
            var client = new UdpClient(rnd.Next()%65000);
            var ip = new IPEndPoint(new IPAddress(new byte[] {8,8,8,8}), 53);
            var loopback = new IPEndPoint(new IPAddress(new byte[] { 127, 0, 0, 1 }), rnd.Next()%65000);
            client.Send(data, data.Length, ip);
            var xyu = client.Receive(ref ip);
            var package = new DnsPackage(xyu);
            var xyu2 = package.ConvertPackageToByte();
            for (var i = 0; i < xyu.Length; i++)
            {
                if(xyu[i] != xyu2[i])Console.WriteLine(i);
            }
            Console.WriteLine(xyu.SequenceEqual(xyu2));
            var package2 = new DnsPackage(xyu2);
        }
    }
}
