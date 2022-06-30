using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Net;
using System.Text;
using System.Xml;

namespace Server
{
    public class DnsPackage
    {
        public Header Header;
        public List<Query> QuestionQueries;
        public List<Query> AuthorityAnswer;
        public List<Query> NonAuthorityAnswer;
        public List<Query> Additional;

        public DnsPackage(int Opcode)
        {
            Header = new Header
            {
                Qr = true,
                Authority = false,
                Opcode = Opcode,
                RecursionAvailable = false,
                Truncated = false,
                RecursionDesired = false
            };
            QuestionQueries = new List<Query>();
            AuthorityAnswer = new List<Query>();
            NonAuthorityAnswer = new List<Query>();
            Additional = new List<Query>();
        }

        public DnsPackage(IReadOnlyList<byte> data)
        {
            Header = new Header(data);
            QuestionQueries = new List<Query>();
            AuthorityAnswer = new List<Query>();
            NonAuthorityAnswer = new List<Query>();
            Additional = new List<Query>();
            var k = 12;
            while (Header.QuestionCount > QuestionQueries.Count)
                QuestionQueries.Add(Query.ParseAnswer(data, ref k, false));
            while (Header.AnswerCount > NonAuthorityAnswer.Count)
            {
                var query = Query.ParseAnswer(data, ref k, true);
                if (query != null)
                    NonAuthorityAnswer.Add(query);
            }

            while (Header.AuthorityCount > AuthorityAnswer.Count)
            {
                var query = Query.ParseAnswer(data, ref k, true);
                if (query != null)
                    AuthorityAnswer.Add(query);
            }

            while (Header.AdditionalCount > Additional.Count)
            {
                var query = Query.ParseAnswer(data, ref k, true);
                if (query != null)
                    Additional.Add(query);
            }
        }

       
        public byte[] ConvertPackageToByte()
        {
            Header.AdditionalCount = Additional.Count;
            Header.QuestionCount = QuestionQueries.Count;
            Header.AnswerCount = NonAuthorityAnswer.Count;
            Header.AuthorityCount = AuthorityAnswer.Count;
            var packageInByte = Header.ConvertToByte().ToList();
            var labels = new Dictionary<string[], int>(new MyArrayComparator());
            var k = 12;
            foreach (var array in QuestionQueries.Select(q => q.ConvertToByte(labels,ref k))) packageInByte.AddRange(array);
            foreach (var array in NonAuthorityAnswer.Select(q => q.ConvertToByte(labels, ref k))) packageInByte.AddRange(array);
            foreach (var array in AuthorityAnswer.Select(q => q.ConvertToByte(labels, ref k))) packageInByte.AddRange(array);
            foreach (var array in Additional.Select(q => q.ConvertToByte(labels, ref k))) packageInByte.AddRange(array);
            return packageInByte.ToArray();
        }
    }
}