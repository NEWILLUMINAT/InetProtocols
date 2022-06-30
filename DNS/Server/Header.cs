using System;
using System.Collections.Generic;
using System.Reflection.Emit;

namespace Server
{
    public class Header
    {
        public int Id { get; set; }

        //Является ли пакет ответом
        public bool Qr { get; set; }

        //Код который копируется из запроса
        public int Opcode { get; set; }

        public bool Truncated { get; set; }

        //Запрос рекурсии
        public bool RecursionDesired { get; set; }

        //Есть ли рекурсия на сервере
        public bool RecursionAvailable { get; set; }
        public int Z { get; set; }
        public bool Authority { get; set; }

        //Код ошибки
        public int RCode { get; set; }
        public int QuestionCount { get; set; }
        public int AnswerCount { get; set; }
        public int AdditionalCount { get; set; }
        public int AuthorityCount { get; set; }

        public Header(IReadOnlyList<byte> data)
        {
            Id = data[0] * 256 + data[1];
            Qr = (data[2] & 128) == 1;
            Opcode = data[2] & 120;
            Truncated = (data[2] & 2) == 1;
            RecursionDesired = (data[2] & 1) == 1;
            QuestionCount = data[4] * 256 + data[5];
            AnswerCount = data[6] * 256 + data[7];
            AuthorityCount = data[8] * 256 + data[9];
            AdditionalCount = data[10] * 256 + data[11];
            Authority = false;
            Z = 0;
        }

        public Header()
        {
            var rnd = new Random();
            Id = rnd.Next();
        }

        public IEnumerable<byte> ConvertToByte()
        {
            var data = new List<byte>();
            if (data == null) throw new ArgumentNullException(nameof(data));
            data.Add((byte)(Id / 256));
            data.Add((byte)(Id % 256));
            data.Add((byte)((Qr ? 1 : 0) * 128 +
                            Opcode * 120 +
                            (Authority ? 1 : 0) * 4 +
                            (Truncated ? 1 : 0) * 2 +
                            (RecursionDesired ? 1 : 0)));
            data.Add((byte)((RecursionAvailable ? 1 : 0) * 128 + Z * 120 + Opcode));
            data.Add((byte)(QuestionCount / 256));
            data.Add((byte)(QuestionCount % 256));
            data.Add((byte)(AnswerCount / 256));
            data.Add((byte)(AnswerCount % 256));
            data.Add((byte)(AuthorityCount / 256));
            data.Add((byte)(AuthorityCount % 256));
            data.Add((byte)(AdditionalCount / 256));
            data.Add((byte)(AdditionalCount % 256));

            return data.ToArray();
        }
    }
}