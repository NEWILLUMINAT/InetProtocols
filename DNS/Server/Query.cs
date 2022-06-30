using System;
using System.Collections.Generic;
using System.Data.Common;
using System.Linq;
using System.Text;
using System.Windows.Markup;
using System.Xml;

namespace Server
{
    public class Query
    {
        public Query()
        {
            Class = new byte[] { 0, 1 };
        }

        public static Query ParseAnswer(IReadOnlyList<byte> data, ref int k, bool isAnswer)
        {
            if (k > data.Count - 1) return null;
            var result = new Query();
            var builder = new StringBuilder();
            var labelLast = ParseName(data, ref k, ref builder);

            if (!labelLast) k++;
            result.Name = builder.ToString();
            result.Type = GetQueryTypeFromByte(data[k], data[k + 1]);
            result.Class = new[] { data[k + 2], data[k + 3] };
            if (isAnswer)
            {
                result.TTL = data[k + 4] * 16777216 + data[k + 5] * 65536 + data[k + 6] * 256 + data[k + 7];
                var dataLength = data[k + 8] * 256 + data[k + 9];
                k += 10;
                if (result.Type == QueryType.Ns)
                {
                    var ch = k;
                    builder.Clear();
                    ParseName(data, ref k, ref builder);
                    var rData = new List<byte>();
                    foreach (var member in builder.ToString().Split('.'))
                    {
                        rData.Add((byte)member.Length);
                        for (var i = 0; i < member.Length; i++)
                            rData.Add((byte)char.ConvertToUtf32(member, i));
                    }

                    rData.Add(0);
                    result.Data = rData.ToArray();
                    if (ch + dataLength != k) k += 1;
                }
                else if (result.Type == QueryType.Mx)
                {
                    var ch = k;
                    builder.Clear();
                    var rData = new List<byte>
                    {
                        data[k],
                        data[k + 1]
                    };
                    k += 2;
                    ParseName(data, ref k, ref builder);
                    foreach (var member in builder.ToString().Split('.'))
                    {
                        rData.Add((byte)member.Length);
                        for (var i = 0; i < member.Length; i++) rData.Add((byte)char.ConvertToUtf32(member, i));
                    }

                    rData.Add(0);
                    result.Data = rData.ToArray();
                    if (ch + dataLength != k) k += 1;
                }
                else
                {
                    result.Data = new byte[dataLength];
                    for (var i = 0; i < dataLength; i++)
                    {
                        result.Data[i] = data[k + i];
                    }

                    k += dataLength;
                }
            }
            else
            {
                k += 4;
            }

            return result;
        }

        private static bool ParseName(IReadOnlyList<byte> data, ref int k, ref StringBuilder builder)
        {
            var labelLast = false;
            while (data[k] != 0)
            {
                if ((data[k] & 192) == 192)
                {
                    var x = (data[k] & 63) + data[k + 1];
                    var nextBuilder = new StringBuilder();
                    ParseName(data, ref x, ref nextBuilder);
                    builder.Append(nextBuilder);
                    k += 2;
                    labelLast = true;
                    break;
                }

                for (var i = 1; i <= data[k]; i++)
                {
                    builder.Append(char.ConvertFromUtf32(data[k + i]));
                }

                k += data[k] + 1;
                if (data[k] != 0) builder.Append('.');
            }

            return labelLast;
        }

        public string Name { get; set; }
        public QueryType Type { get; set; }
        public byte[] Class;
        public int TTL { get; set; }

        public int RData => Data.Length;

        public byte[] Data;

        public enum QueryType
        {
            A,
            Aaaa,
            Ns,
            Ptr,
            Cname,
            Soa,
            Wks,
            Hinfo,
            Minfo,
            Mx,
            Txt,
            Error
        }

        private static QueryType GetQueryTypeFromByte(byte first, byte second)
        {
            switch (second)
            {
                case 1:
                    return QueryType.A;
                case 2:
                    return QueryType.Ns;
                case 6:
                    return QueryType.Soa;
                case 15:
                    return QueryType.Mx;
                case 28:
                    return QueryType.Aaaa;
                default:
                    return QueryType.Error;
            }
        }

        private static IEnumerable<byte> GetByteFromQueryType(QueryType type)
        {
            switch (type)
            {
                case QueryType.A:
                    return new byte[] { 0, 1 };
                case QueryType.Ns:
                    return new byte[] { 0, 2 };
                case QueryType.Aaaa:
                    return new byte[] { 0, 28 };
                case QueryType.Ptr:
                    return new byte[] { 0, 12 };
                case QueryType.Cname:
                    return new byte[] { 0, 5 };
                case QueryType.Soa:
                    return new byte[] { 0, 6 };
                case QueryType.Wks:
                    return new byte[] { 0, 11 };
                case QueryType.Hinfo:
                    return new byte[] { 0, 13 };
                case QueryType.Minfo:
                    return new byte[] { 0, 14 };
                case QueryType.Mx:
                    return new byte[] { 0, 15 };
                case QueryType.Txt:
                    return new byte[] { 0, 16 };
                case QueryType.Error:
                    return new byte[] { };
                default:
                    throw new ArgumentException();
            }
        }

        public byte[] ConvertToByte(Dictionary<string[], int> labels, ref int k)
        {
            var answer = new List<byte>();
            var splitName = Name.Split('.');
            var labelLast = false;
            for (var i = 0; i < splitName.Length; i++)
            {
                var array = splitName.Skip(i).ToArray();
                if (labels.ContainsKey(array))
                {
                    var firstLabel = (byte)((labels[array] >> 8) | 192);
                    var secondLabel = (byte)(labels[array] & 255);
                    answer.Add(firstLabel);
                    answer.Add(secondLabel);
                    labelLast = true;
                    break;
                }
                var member = splitName[i];
                answer.Add((byte)member.Length);
                for (var j = 0; j < member.Length; j++)
                    answer.Add((byte)char.ConvertToUtf32(member, j));
            }

            AddLabels(Name, labels, k);
            if (!labelLast) answer.Add(0);
            answer.AddRange(GetByteFromQueryType(Type));
            answer.AddRange(Class);
            if (TTL == 0)
            {
                k += answer.Count;
                return answer.ToArray();
            }

            answer.Add(Convert.ToByte(TTL >> 24));
            answer.Add(Convert.ToByte((TTL & 16711680) >> 16));
            answer.Add(Convert.ToByte((TTL & 65280) >> 8));
            answer.Add(Convert.ToByte(TTL & 255));
            if (Type == QueryType.Ns)
            {
                var l = k + answer.Count + 3;
                var nsData = ParseNsName(Data,labels, ref l);
                var rData = nsData.Length;
                answer.AddRange(new[] { (byte)(rData & 65280), (byte)(rData & 255) });
                answer.AddRange(nsData);
            }
            // else if (Type == QueryType.Mx)
            // {
            //     var l = k + answer.Count + 5;
            //     var mxData = ParseNsName(Data.Skip(2).ToArray(), labels, ref l);
            //     var rData = mxData.Length + 2;
            //     answer.AddRange(new[] { (byte)(rData & 65280), (byte)(rData & 255) });
            //     answer.Add(Data[0]);
            //     answer.Add(Data[1]);
            //     answer.AddRange(mxData);
            // }
            else
            {
                answer.AddRange(new[] { (byte)(RData & 65280), (byte)(RData & 255) });
                answer.AddRange(Data);
            }
            k += answer.Count;
            return answer.ToArray();
        }

        private byte[] ParseNsName(IReadOnlyList<byte> data, Dictionary<string[], int> labels, ref int k)
        {
            var l = 0;
            var labelLast = false;
            var builder = new StringBuilder();
            var answer = new List<byte>();
            ParseName(data, ref l, ref builder);
            var splitName = builder.ToString().Split('.');

            for (var i = 0; i < splitName.Length; i++)
            {
                var array = splitName.Skip(i).ToArray();
                if (labels.ContainsKey(array))
                {
                    var firstLabel = (byte)((labels[array] >> 8) | 192);
                    var secondLabel = (byte)(labels[array] & 255);
                    answer.Add(firstLabel);
                    answer.Add(secondLabel);
                    labelLast = true;
                    break;
                }

                var member = splitName[i];
                answer.Add((byte)member.Length);
                for (var j = 0; j < member.Length; j++)
                    answer.Add((byte)char.ConvertToUtf32(member, j));
            }

            AddLabels(builder.ToString(), labels, k);
            if (!labelLast) answer.Add(0);
            return answer.ToArray();
        }

        private void AddLabels(string name, Dictionary<string[], int> labels, int k)
        {
            var pointer = k;
            var splitName = name.Split('.');
            for (var i = 0; i < splitName.Length; i++)
            {
                var array = splitName.Skip(i).ToArray();
                if (!labels.ContainsKey(array)) labels.Add(array, pointer);
                pointer += splitName[i].Length;
                if (k == 12) pointer++;
            }
        }

        public override bool Equals(object obj)
        {
            if (obj == null || obj.GetType() != GetType()) return false;
            var another = (Query)obj;
            if (GetHashCode() != another.GetHashCode()) return false;
            return Type == another.Type && Name == another.Name;
        }

        public override int GetHashCode()
        {
            return new Tuple<string, QueryType>(Name, Type).GetHashCode();
            //return base.GetHashCode();
        }
    }

    public class MyArrayComparator : IEqualityComparer<string[]>
    {
        public bool Equals(string[] x, string[] y)
        {
            if (y == null || x == null || x.Length != y.Length) return false;
            return !x.Where((t, i) => !t.Equals(y[i])).Any();
        }

        public int GetHashCode(string[] obj)
        {
            unchecked
            {
                int sum = 0;
                foreach (var x in obj) sum += x.GetHashCode();

                return sum;
            }
        }
    }
}