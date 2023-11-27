import os
from typing import Optional
import tempfile
import unittest
import unittest.mock

from medcat.cat import CAT
from medcat.cdb import CDB
from medcat.vocab import Vocab
from medcat.config import Config


class CDBHashingTests(unittest.TestCase):
    temp_dir = tempfile.TemporaryDirectory()

    @classmethod
    def setUpClass(cls) -> None:
        cls.cdb = CDB.load(os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "..", "..", "examples", "cdb.dat"))

    def test_recalc_hash_same(self):
        h1 = self.cdb.get_hash(force_recalc=True)
        h2 = self.cdb.get_hash(force_recalc=True)
        self.assertEqual(h1, h2)

    def test_CDB_hash_saves_on_disk(self):
        h = self.cdb.get_hash(force_recalc=True)  # make sure there's a hash
        temp_file = os.path.join(self.temp_dir.name, 'cdb.dat')
        self.cdb.save(temp_file)

        cdb = CDB.load(temp_file)
        self.assertEqual(h, cdb._hash)


class CDBHashingWithConfigTests(unittest.TestCase):
    temp_dir = tempfile.TemporaryDirectory()

    @classmethod
    def setUpClass(cls) -> None:
        cls.cdb = CDB.load(os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "..", "..", "examples", "cdb.dat"))
        # ensure config has hash
        h = cls.cdb.get_hash()
        cls.config = cls.config_copy(cls.cdb.config)
        cls._config_hash = cls.cdb.config.hash

    @classmethod
    def config_copy(cls, config: Optional[Config] = None) -> Config:
        if config is None:
            config = cls.config
        return Config(**config.asdict())

    def setUp(self) -> None:
        # reset config
        self.cdb.config = self.config_copy()
        # reset config hash
        self.cdb._config_hash = self._config_hash
        self.cdb.config.hash = self._config_hash

    def test_CDB_same_hash_no_need_recalc(self):
        self.assertFalse(self.cdb._should_recalc_hash(force_recalc=False))

    def test_CDB_hash_recalc_if_no_config_hash(self):
        self.cdb._config_hash = None
        self.assertTrue(self.cdb._should_recalc_hash(force_recalc=False))

    def test_CDB_hash_recalc_after_config_change(self):
        self.cdb.config.linking.filters.cuis = {"a", "b", "c"}
        self.assertTrue(self.cdb._should_recalc_hash(force_recalc=False))


class BaseCATHashingTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.cdb = CDB.load(os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "..", "..", "examples", "cdb.dat"))
        cls.vocab = Vocab.load(os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "..", "..",  "examples", "vocab.dat"))
        cls.cdb.config.general.spacy_model = "en_core_web_md"
        cls.cdb.config.ner.min_name_len = 2
        cls.cdb.config.ner.upper_case_limit_len = 3
        cls.cdb.config.general.spell_check = True
        cls.cdb.config.linking.train_count_threshold = 10
        cls.cdb.config.linking.similarity_threshold = 0.3
        cls.cdb.config.linking.train = True
        cls.cdb.config.linking.disamb_length_limit = 5
        cls.cdb.config.general.full_unlink = True
        cls.undertest = CAT(
            cdb=cls.cdb, config=cls.cdb.config, vocab=cls.vocab)


class CATHashingTestsWithFakeHash(BaseCATHashingTests):
    _fake_hash = 'ffff0000'

    def setUp(self) -> None:
        self.undertest.cdb._hash = self._fake_hash

    def tearDown(self) -> None:
        self.undertest.cdb._hash = None  # TODO what if under test has a hash?


class CATHashingTestsWithoutChangeRecalc(CATHashingTestsWithFakeHash):

    def test_no_changes_can_recalc(self):
        h = self.undertest.get_hash(force_recalc=True)
        self.assertIsInstance(h, str)

    def test_no_changes_recalc_same(self):
        h1 = self.undertest.get_hash(force_recalc=True)
        h2 = self.undertest.get_hash(force_recalc=True)
        self.assertEqual(h1, h2)


class CATHashingTestsWithoutChange(CATHashingTestsWithFakeHash):

    def setUp(self) -> None:
        self._calculate_hash = self.undertest.cdb.calculate_hash
        # make sure the hash exists
        self.undertest.cdb._config_hash = self.undertest.cdb.config.get_hash()
        self.undertest.cdb.get_hash()
        self.undertest.cdb.calculate_hash = unittest.mock.Mock()

    def test_no_changes_no_calc(self):
        hash = self.undertest.get_hash()
        self.assertIsInstance(hash, str)
        self.undertest.cdb.calculate_hash.assert_not_called()


class CATHashingTestsWithChange(CATHashingTestsWithFakeHash):
    # {name: {'tokens': tokens, 'snames': snames, 'raw_name': raw_name}, ...}
    concept_kwargs = dict(cui='C1232', names={'c1232-name': {'tokens': {},
                                                             'snames': 'c1232-name', 'raw_name': 'c1232-name', 'is_upper': False}},
                          ontologies=set(), name_status='P', type_ids=set(), description='TEST')

    def test_when_changes_do_calc(self):
        with unittest.mock.patch.object(CDB, 'calculate_hash', return_value='abcd1234') as patch_method:
            self.undertest.cdb._add_concept(**self.concept_kwargs)
            hash = self.undertest.get_hash()
        self.assertIsInstance(hash, str)
        patch_method.assert_called()


class CATDirtTestsWithChange(CATHashingTestsWithFakeHash):
    # {name: {'tokens': tokens, 'snames': snames, 'raw_name': raw_name}, ...}
    concept_kwargs = dict(cui='C1232', names={'c1232-name': {'tokens': {},
                                                             'snames': 'c1232-name', 'raw_name': 'c1232-name', 'is_upper': False}},
                          ontologies=set(), name_status='P', type_ids=set(), description='TEST')

    def test_default_cdb_not_dirty(self):
        self.assertFalse(self.undertest.cdb.is_dirty)

    def test_after_add_concept_is_dirty(self):
        self.undertest.cdb._add_concept(**self.concept_kwargs)
        self.assertTrue(self.undertest.cdb.is_dirty)

    def test_after_recalc_not_dirty(self):
        self.undertest.cdb._add_concept(**self.concept_kwargs)
        self.undertest.get_hash()
        self.assertFalse(self.undertest.cdb.is_dirty)
