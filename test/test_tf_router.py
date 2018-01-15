import os
import re
import shutil
import tempfile
import unittest
from string import ascii_lowercase
from subprocess import check_call, check_output
from hashlib import sha1

from hypothesis import example, given
from hypothesis.strategies import fixed_dictionaries, text


def template_to_re(t):
    """
    Takes a template (i.e. what you'd call `.format(...)` on, and
    returns a regex to to match it:
        print(re.match(
            template_to_re("hello {name}"),
            "hello world"
        ).group("name"))
        # prints "world"
    """
    seen = dict()

    def pattern(placeholder, open_curly, close_curly, text):
        if text is not None:
            return re.escape(text)
        elif open_curly is not None:
            return r'\{'
        elif close_curly is not None:
            return r'\}'
        elif seen.get(placeholder):
            return '(?P={})'.format(placeholder)
        else:
            seen[placeholder] = True
            return '(?P<{}>.*?)'.format(placeholder)

    return "".join([
        pattern(*match.groups())
        for match in re.finditer(r'{([\w_]+)}|(\{\{)|(\}\})|([^{}]+)', t)
    ])


class TestTFRouter(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        cls.workdir = tempfile.mkdtemp()
        cls.base_path = os.getcwd()
        cls.module_path = os.path.join(os.getcwd(), 'test', 'infra')

        check_call(['terraform', 'init', cls.module_path], cwd=cls.workdir)

    @classmethod
    def teardown_class(cls):
        try:
            shutil.rmtree(cls.workdir)
        except Exception as e:
            print('Error removing {}: {}', cls.workdir, e)

    def _env_for_check_output(self):
        env = os.environ.copy()
        return env

    def _target_module(self, target):
        submodules = [
            "default_backend_task_definition",
            "alb"
        ]
        return [
            '-target=module.{}.module.{}'.format(target, submodule)
            for submodule in submodules
        ]

    def test_create_correct_number_of_resources(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=dev',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.router.module.alb.aws_alb.alb', # noqa
        ] + [self.module_path], env=self._env_for_check_output(),
        cwd=self.workdir).decode('utf-8')

        # Then
        assert """
Plan: 2 to add, 0 to change, 0 to destroy.
        """.strip() in output

    @given(fixed_dictionaries({
        'environment': text(alphabet=ascii_lowercase, min_size=1),
        'component': text(alphabet=ascii_lowercase+'-', min_size=1).filter(
            lambda c: not(c.startswith('-') or c.endswith('-'))
        ),
        'team': text(alphabet=ascii_lowercase+'-', min_size=1).filter(
            lambda c: len(c.replace('-', ''))
        ),
    }))
    @example({
        'environment': 'live',
        'component': 'a'*21,
        'team': 'kubric',
    })
    def test_create_public_alb_in_public_subnets(self, fixtures):
        # Given
        env = fixtures['environment']
        component = fixtures['component']
        team = fixtures['team']

        desired_name = '{}-{}'.format(env, component)
        if len(desired_name) <= 32:
            expected_name = desired_name
        else:
            expected_name = desired_name[0:24] + \
                            sha1(desired_name.encode('utf-8')).hexdigest()[0:8]

        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env={}'.format(env),
            '-var', 'component={}'.format(component),
            '-var', 'team={}'.format(team),
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.router.module.alb.aws_alb.alb', # noqa
        ] + [self.module_path], env=self._env_for_check_output(),
        cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
+ module.router.module.alb.aws_alb.alb
      id:                                    <computed>
      access_logs.#:                         "1"
      access_logs.0.enabled:                 "false"
      arn:                                   <computed>
      arn_suffix:                            <computed>
      dns_name:                              <computed>
      enable_deletion_protection:            "false"
      idle_timeout:                          "60"
      internal:                              "false"
      ip_address_type:                       <computed>
      name:                                  "{}"
      security_groups.#:                     <computed>
      subnets.#:                             "3"
      subnets.{{ident1}}:                    "subnet-55555555"
      subnets.{{ident2}}:                    "subnet-33333333"
      subnets.{{ident3}}:                    "subnet-44444444"
      tags.%:                                "3"
      tags.component:                        "{}"
      tags.environment:                      "{}"
      tags.team:                             "{}"
      vpc_id:                                <computed>
      zone_id:                               <computed>
        """.format(expected_name, component, env, team).strip()), output) # noqa

    def test_create_public_alb_listener(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-target=module.router.module.alb.aws_alb_listener.https',
            '-no-color',
            self.module_path
        ], env=self._env_for_check_output(),
        cwd=self.workdir).decode('utf-8')

        # Then
        assert """
  + module.router.module.alb.aws_alb_listener.https
      id:                                    <computed>
      arn:                                   <computed>
      certificate_arn:                       "${module.aws_acm_certificate_arn.arn}"
      default_action.#:                      "1"
      default_action.0.target_group_arn:     "${var.default_target_group_arn}"
      default_action.0.type:                 "forward"
      load_balancer_arn:                     "${aws_alb.alb.arn}"
      port:                                  "443"
      protocol:                              "HTTPS"
      ssl_policy:                            <computed>
        """.strip() in output # noqa

    def test_create_public_alb_security_group(self):
        # When
        output = check_output([
            'terraform',
            'plan',
            '-var', 'env=foo',
            '-var', 'component=foobar',
            '-var', 'team=foobar',
            '-var', 'alb_domain=domain.com',
            '-var-file={}/test/platform-config/eu-west-1.json'.format(
                self.base_path
            ),
            '-no-color',
            '-target=module.router.module.alb.aws_security_group.default', # noqa
        ] + [self.module_path], env=self._env_for_check_output(),
        cwd=self.workdir).decode('utf-8')

        # Then
        assert re.search(template_to_re("""
  + module.router.module.alb.aws_security_group.default
      id:                                    <computed>
      description:                           "Managed by Terraform"
      egress.#:                              "1"
      egress.{ident1}.cidr_blocks.#:        "1"
      egress.{ident1}.cidr_blocks.0:        "0.0.0.0/0"
      egress.{ident1}.from_port:            "0"
      egress.{ident1}.ipv6_cidr_blocks.#:   "0"
      egress.{ident1}.prefix_list_ids.#:    "0"
      egress.{ident1}.protocol:             "-1"
      egress.{ident1}.security_groups.#:    "0"
      egress.{ident1}.self:                 "false"
      egress.{ident1}.to_port:              "0"
      ingress.#:                             "2"
      ingress.{ident2}.cidr_blocks.#:      "1"
      ingress.{ident2}.cidr_blocks.0:      "0.0.0.0/0"
      ingress.{ident2}.from_port:          "80"
      ingress.{ident2}.ipv6_cidr_blocks.#: "0"
      ingress.{ident2}.protocol:           "tcp"
      ingress.{ident2}.security_groups.#:  "0"
      ingress.{ident2}.self:               "false"
      ingress.{ident2}.to_port:            "80"
      ingress.{ident3}.cidr_blocks.#:      "1"
      ingress.{ident3}.cidr_blocks.0:      "0.0.0.0/0"
      ingress.{ident3}.from_port:          "443"
      ingress.{ident3}.ipv6_cidr_blocks.#: "0"
      ingress.{ident3}.protocol:           "tcp"
      ingress.{ident3}.security_groups.#:  "0"
      ingress.{ident3}.self:               "false"
      ingress.{ident3}.to_port:            "443"
      name:                                  <computed>
      owner_id:                              <computed>
      vpc_id:                                "vpc-12345678"
        """.strip()), output) # noqa
