import ConfigParser
import unittest


class TestConfigurationFile(unittest.TestCase):

    def setUp(self):
        self.config = ConfigParser.RawConfigParser(allow_no_value=False)
        self.config.read('load_balancer.cfg.template')

    def test_sections(self):
        self.assertEqual(self.config.has_section('openstack'), True)
        self.assertEqual(self.config.has_section('monitoring'), True)
        self.assertEqual(self.config.has_section('infrastructure'), True)
        self.assertEqual(self.config.has_section('heuristic'), True),

    def test_openstack_section(self):
        opts = ['username', 'password', 'user_domain_name', 'project_name',
                'project_domain_name', 'auth_url']
        for option in opts:
            self.assertTrue(self.config.get('openstack', option))

    def test_monitoring_section(self):
        opts = ['username', 'password', 'project_name', 'monasca_api_version',
                'auth_url']

        for option in opts:
            self.assertTrue(self.config.get('monitoring', option))

    def test_infrastructure_section(self):
        self.assertTrue(self.config.get('infrastructure', 'hosts'))

    def test_heuristic_section(self):
        opts = ['module', 'class']
        for option in opts:
            self.assertTrue(self.config.get('heuristic', option))
