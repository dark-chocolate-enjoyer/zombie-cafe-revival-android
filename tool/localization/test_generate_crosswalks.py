#!/usr/bin/env python3
"""Unit tests for the translation-memory behavior of generate_crosswalks.py.

Run: python3 -m unittest tool.localization.test_generate_crosswalks
 (or: python3 -m unittest discover tool/localization)

The invariants under test are the ones the translation workflow relies on:
 1. a reviewed proposed_english is never lost on regeneration (TM carry);
 2. regular TM never replaces a non-empty auto proposal;
 3. --tm-override entries do replace auto proposals (human review wins);
 4. placeholder validation flags any token-multiplicity change;
 5. quest TM rows keep literal_note/confidence/review_note through regen.
"""
import csv
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_crosswalks as gc  # noqa: E402


def write_tm(path, rows, hdr=('source_file', 'field', 'jp_text', 'proposed_english')):
    with open(path, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(hdr)
        w.writerows(rows)


class TMTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _tm(self, name, rows, hdr=None):
        path = os.path.join(self.tmp.name, name)
        if hdr:
            write_tm(path, rows, hdr)
        else:
            write_tm(path, rows)
        return path

    def test_tm_fills_empty_and_preserves_reviewed_value(self):
        tm = gc.load_tm([self._tm('a.csv', [
            ['f.bin', 'Name', '毒のタル', 'Toxic barrel']])])
        rows = [['f.bin', 0, 'Name', '毒のタル', '', '', 'jp_only_event', 'low', '']]
        filled = gc.apply_tm(tm, rows)
        self.assertEqual(filled, 1)
        self.assertEqual(rows[0][5], 'Toxic barrel')

    def test_regular_tm_never_replaces_nonempty_proposal(self):
        tm = gc.load_tm([self._tm('a.csv', [
            ['f.bin', 'Name', '毒のタル', 'WRONG DRAFT']])])
        rows = [['f.bin', 0, 'Name', '毒のタル', 'Toxic barrel', 'Toxic barrel',
                 'direct_english_row', 'high', '']]
        gc.apply_tm(tm, rows)
        self.assertEqual(rows[0][5], 'Toxic barrel')

    def test_later_tm_file_wins_key_collisions(self):
        tm = gc.load_tm([
            self._tm('old.csv', [['f.bin', 'Name', 'X', 'old value']]),
            self._tm('new.csv', [['f.bin', 'Name', 'X', 'reviewed value']]),
        ])
        self.assertEqual(gc.tm_lookup(tm, 'f.bin', 'Name', 'X'), 'reviewed value')

    def test_override_replaces_auto_proposal_and_notes_it(self):
        override = gc.load_tm([self._tm('o.csv', [
            ['f.bin', 'Name', '新イベントの鉢植え２(小)', 'Event Planter 2 (Small)']])])
        rows = [['f.bin', 0, 'Name', '新イベントの鉢植え２(小)', 'Planter', 'Planter',
                 'same_art_or_category', 'medium', '']]
        filled = gc.apply_tm({}, rows, override)
        self.assertEqual(filled, 1)
        self.assertEqual(rows[0][5], 'Event Planter 2 (Small)')
        self.assertIn('replaced by reviewed override', rows[0][8])

    def test_per_row_tm_key_beats_shared_jp_name(self):
        # Two records share one JP name but carry different EN values; the
        # per-row key must win over the (colliding) name-level key.
        tm = gc.load_tm([self._tm('a.csv', [
            ['f.bin', '238', 'Name', 'ヒッピーのポスター', 'Hippie Poster 1'],
            ['f.bin', '239', 'Name', 'ヒッピーのポスター', 'Hippie Poster 2']],
            hdr=['source_file', 'record_index', 'field', 'jp_text', 'proposed_english'])])
        rows = [['f.bin', 238, 'Name', 'ヒッピーのポスター', '', '', 'mt', 'low', ''],
                ['f.bin', 239, 'Name', 'ヒッピーのポスター', '', '', 'mt', 'low', '']]
        gc.apply_tm(tm, rows)
        self.assertEqual(rows[0][5], 'Hippie Poster 1')
        self.assertEqual(rows[1][5], 'Hippie Poster 2')

    def test_placeholder_validation(self):
        self.assertEqual(gc.validate_placeholders('現金を[NUM]＄貯めろ。',
                                                  'Save up $[NUM] in cash.'), '')
        self.assertIn('[NUM]', gc.validate_placeholders('[NUM]個', 'some'))
        self.assertIn('#', gc.validate_placeholders('#店舗', 'shops'))
        self.assertIn('\\', gc.validate_placeholders('あと\\で', 'later'))
        rows = [['s.bin', 0, 'line_0', '[NUM]個', '', '[NUM] and [NUM]',
                 'index_aligned_verified', 'high', '']]
        self.assertEqual(gc.flag_placeholder_mismatches(rows), 1)
        self.assertIn('PLACEHOLDER MISMATCH', rows[0][8])

    def test_quest_tm_preserves_review_columns(self):
        quest_tm_hdr = ['source_file', 'field', 'jp_text', 'proposed_english',
                        'literal_note', 'confidence', 'review_note']
        override = gc.load_tm([self._tm('q.csv', [
            ['assets/data/quest.bin.mid', 'text', '現金を[NUM]＄貯めろ。',
             'Save up $[NUM] in cash.', 'tamero = save up', 'high', 'reviewed']],
            hdr=quest_tm_hdr)])
        quests = [dict(QuestID=0, LevelGate=9, Text='現金を[NUM]＄貯めろ。'),
                  dict(QuestID=1, LevelGate=9, Text='現金を[NUM]＄貯めろ。'),
                  dict(QuestID=2, LevelGate=255, Text='未訳のクエスト')]
        rows, stats = gc.build_quests(quests, {}, override)
        self.assertEqual(stats['templates'], 2)
        self.assertEqual(stats['tm_filled'], 1)
        self.assertEqual(stats['placeholder_mismatches'], 0)
        t0 = rows[0]
        hdr = gc.QUEST_CSV_HDR
        self.assertEqual(t0[hdr.index('usage_count')], 2)
        self.assertEqual(t0[hdr.index('proposed_english')], 'Save up $[NUM] in cash.')
        self.assertEqual(t0[hdr.index('literal_note')], 'tamero = save up')
        self.assertEqual(t0[hdr.index('confidence')], 'high')
        self.assertEqual(t0[hdr.index('review_note')], 'reviewed')
        self.assertEqual(t0[hdr.index('placeholder_check')], 'OK')
        self.assertEqual(rows[1][hdr.index('placeholder_check')], 'PENDING')

    def test_quest_tm_mismatch_is_flagged_not_silently_accepted(self):
        quest_tm_hdr = ['source_file', 'field', 'jp_text', 'proposed_english']
        override = gc.load_tm([self._tm('q.csv', [
            ['assets/data/quest.bin.mid', 'text', '現金を[NUM]＄貯めろ。',
             'Save up cash.']], hdr=quest_tm_hdr)])
        rows, stats = gc.build_quests(
            [dict(QuestID=0, LevelGate=9, Text='現金を[NUM]＄貯めろ。')], {}, override)
        self.assertEqual(stats['placeholder_mismatches'], 1)
        self.assertIn('MISMATCH',
                      rows[0][gc.QUEST_CSV_HDR.index('placeholder_check')])


class QuestDecodeTests(unittest.TestCase):
    def test_read_jp_quests_synthetic_roundtrip_fields(self):
        # one synthetic record in the documented layout
        def s(txt):
            b = txt.encode('utf-8')
            return struct.pack('>h', len(b)) + b
        rec = (struct.pack('>i', 0) + bytes([9, 24]) +
               s('level') + struct.pack('>i', -1) +
               s('na') + struct.pack('>i', -1) +
               s('na') + struct.pack('>i', 1) +
               struct.pack('>h', 1) + struct.pack('>i', -1) + bytes([255]) +
               struct.pack('>i', 1) + struct.pack('>h', 1) +
               struct.pack('>i', -1) + struct.pack('>i', 10000) +
               struct.pack('>i', 1250) + struct.pack('>i', -1) +
               bytes([0]) + struct.pack('>i', -1) + struct.pack('>h', -1) +
               s('現金を[NUM]＄貯めろ。'))
        blob = struct.pack('>h', 1) + rec
        path = os.path.join(tempfile.gettempdir(), 'quest_synth.bin')
        with open(path, 'wb') as fh:
            fh.write(blob)
        try:
            quests = gc.read_jp_quests(path)
        finally:
            os.remove(path)
        self.assertEqual(len(quests), 1)
        self.assertEqual(quests[0]['QuestID'], 0)
        self.assertEqual(quests[0]['LevelGate'], 9)
        self.assertEqual(quests[0]['Text'], '現金を[NUM]＄貯めろ。')


if __name__ == '__main__':
    unittest.main()
