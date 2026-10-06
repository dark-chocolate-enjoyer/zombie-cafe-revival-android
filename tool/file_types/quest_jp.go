package file_types

import (
	"io"
)

// QuestJP is the JP 1.7.0 quest.bin.mid record (HQ missions). The layout was
// derived and validated to exact EOF across all 1,020 records in the pass-2
// schema report (jp/research/pass2_codecs_quests/quest_schema_report.md).
//
// Semantics that are established: QuestID is sequential and equals the record
// index; LevelGate is the cafe level required (255 on filler rows); the three
// condition slots carry the types "level", "premise" or "na"; PremiseQuestID
// is the prerequisite quest when a "premise" condition is present; TargetRef
// is a foodData row for [RECIPE] quests and a characterData row for [CHARA]
// quests; GoalAmount feeds the [NUM] placeholder; Text is the player-facing
// template.
//
// Flag2 is the quest-type enum and is preserved as its raw byte. Fields whose
// meaning is still open (MidA..MidE, TailA..TailC) and
// RewardPacked (an int32 whose high int16 is a Toxin amount and low int16 a
// small count) are kept as raw values: the codec never interprets or
// normalizes them, so a read/write round trip is byte-identical.
type QuestJP struct {
	QuestID        int32
	LevelGate      byte
	Flag2          byte
	Cond1Type      string
	Cond1Value     int32
	Cond2Type      string
	Cond2Value     int32
	Cond3Type      string
	Cond3Value     int32
	MidA           int16
	PremiseQuestID int32
	MidC           byte
	MidD           int32
	MidE           int16
	TargetRef      int32
	GoalAmount     int32
	RewardXP       int32
	RewardPacked   int32
	TailA          byte
	TailB          int32
	TailC          int16
	Text           string
}

func readSingleQuestJP(file io.Reader) QuestJP {
	var quest QuestJP
	quest.QuestID = ReadInt32(file)
	quest.LevelGate = ReadByte(file)
	quest.Flag2 = ReadByte(file)
	quest.Cond1Type = ReadString(file)
	quest.Cond1Value = ReadInt32(file)
	quest.Cond2Type = ReadString(file)
	quest.Cond2Value = ReadInt32(file)
	quest.Cond3Type = ReadString(file)
	quest.Cond3Value = ReadInt32(file)
	quest.MidA = ReadInt16(file)
	quest.PremiseQuestID = ReadInt32(file)
	quest.MidC = ReadByte(file)
	quest.MidD = ReadInt32(file)
	quest.MidE = ReadInt16(file)
	quest.TargetRef = ReadInt32(file)
	quest.GoalAmount = ReadInt32(file)
	quest.RewardXP = ReadInt32(file)
	quest.RewardPacked = ReadInt32(file)
	quest.TailA = ReadByte(file)
	quest.TailB = ReadInt32(file)
	quest.TailC = ReadInt16(file)
	quest.Text = ReadString(file)
	return quest
}

func writeSingleQuestJP(file io.Writer, data QuestJP) {
	WriteInt32(file, data.QuestID)
	WriteByte(file, data.LevelGate)
	WriteByte(file, data.Flag2)
	WriteString(file, data.Cond1Type)
	WriteInt32(file, data.Cond1Value)
	WriteString(file, data.Cond2Type)
	WriteInt32(file, data.Cond2Value)
	WriteString(file, data.Cond3Type)
	WriteInt32(file, data.Cond3Value)
	WriteInt16(file, data.MidA)
	WriteInt32(file, data.PremiseQuestID)
	WriteByte(file, data.MidC)
	WriteInt32(file, data.MidD)
	WriteInt16(file, data.MidE)
	WriteInt32(file, data.TargetRef)
	WriteInt32(file, data.GoalAmount)
	WriteInt32(file, data.RewardXP)
	WriteInt32(file, data.RewardPacked)
	WriteByte(file, data.TailA)
	WriteInt32(file, data.TailB)
	WriteInt16(file, data.TailC)
	WriteString(file, data.Text)
}

func ReadQuestsJP(file io.Reader) []QuestJP {
	num := int(ReadInt16(file))
	data := []QuestJP{}

	for i := 0; i < num; i++ {
		data = append(data, readSingleQuestJP(file))
	}

	return data
}

func WriteQuestsJP(file io.Writer, quests []QuestJP) {
	WriteInt16(file, int16(len(quests)))

	for i := 0; i < len(quests); i++ {
		writeSingleQuestJP(file, quests[i])
	}
}
