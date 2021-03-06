#!/usr/bin/env python

#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Lists the most recent versions in the deliverable files.
"""

from __future__ import print_function

import argparse
import os.path
import re
import subprocess

import yaml


PRE_RELEASE_RE = re.compile('''
    \.(\d+(?:[ab]|rc)+\d*)$
''', flags=re.VERBOSE | re.UNICODE)


def find_modified_deliverable_files(reporoot):
    "Return a list of files modified by the most recent commit."
    results = subprocess.check_output(
        ['git', 'diff', '--name-only', '--pretty=format:', 'HEAD^'],
        cwd=reporoot,
    )
    filenames = [
        l.strip()
        for l in results.splitlines()
        if l.startswith('deliverables/')
    ]
    return filenames


def get_modified_deliverable_file_content(reporoot, filenames):
    """Return a sequence of tuples containing the new versions.

    Return tuples containing (deliverable name, series name, version
    number, repository name, hash SHA, include pypi link, first full
    version)

    """
    # Determine which deliverable files to process by taking our
    # command line arguments or by scanning the git repository
    # for the most recent change.
    deliverable_files = filenames
    if not deliverable_files:
        deliverable_files = find_modified_deliverable_files(
            reporoot
        )

    for basename in deliverable_files:
        filename = os.path.join(reporoot, basename)
        if not os.path.exists(filename):
            # The file must have been deleted, skip it.
            continue
        with open(filename, 'r') as f:
            deliverable_data = yaml.load(f.read())

        # Determine whether announcements should include a PyPI
        # link. Default to no, for service projects, because it is
        # less irksome to fail to include a link to a thing that
        # exists than to link to something that does not.
        include_pypi_link = deliverable_data.get(
            'include-pypi-link',
            False,
        )
        include_pypi_link = 'yes' if include_pypi_link else 'no'

        # The series name is part of the filename, rather than the file
        # body. That causes release.sh to be called with series="_independent"
        # for release:independent projects, and release.sh to use master branch
        # to evaluate fixed bugs.
        series_name = os.path.basename(
            os.path.dirname(os.path.abspath(filename))
        ).lstrip('_')
        deliverable_name = os.path.splitext(os.path.basename(filename))[0]

        all_versions = {
            rel['version']: rel for rel in deliverable_data['releases']
        }
        version = deliverable_data['releases'][-1]['version']
        this_version = all_versions[version]
        final_versions = [
            r['version']
            for r in deliverable_data['releases']
            if not PRE_RELEASE_RE.search(r['version'])
        ]
        first_full_release = 'yes' if (
            final_versions and
            this_version['version'] == final_versions[0]
        ) else 'no'
        diff_start = this_version.get('diff-start', '-')
        for project in this_version['projects']:
            yield (deliverable_name, series_name, version,
                   diff_start,
                   project['repo'], project['hash'],
                   include_pypi_link,
                   first_full_release)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'deliverable_file',
        nargs='*',
        help='paths to YAML files specifying releases',
    )
    parser.add_argument(
        '--releases-repo', '-r',
        default='.',
        help='path to the releases repository for automatic scanning',
    )
    args = parser.parse_args()

    results = get_modified_deliverable_file_content(
        args.releases_repo,
        args.deliverable_file,
    )
    for r in results:
        print(' '.join(r))
    return 0


if __name__ == '__main__':
    main()
