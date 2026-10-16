#
# spec file for package python-stormssh
#
# Copyright (c) 2014 SUSE LINUX Products GmbH, Nuernberg, Germany.
# Copyright (c) 2026 storm contributors
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via https://github.com/intrepidsilence/storm/issues


%{?sle15_python_module_pythons}
Name:           python-stormssh
Version:        1.2.0
Release:        0
Summary:        Command line tool to manage your ssh connections
License:        MIT
URL:            https://github.com/intrepidsilence/storm
Source:         https://github.com/intrepidsilence/storm/archive/refs/tags/v%{version}.tar.gz#/stormssh-%{version}.tar.gz
BuildRequires:  %{python_module pip}
BuildRequires:  %{python_module setuptools >= 68}
BuildRequires:  %{python_module wheel}
BuildRequires:  fdupes
BuildRequires:  python-rpm-macros
# SECTION test requirements
BuildRequires:  %{python_module Flask >= 3.0}
BuildRequires:  %{python_module paramiko >= 3.4}
BuildRequires:  %{python_module pytest}
BuildRequires:  %{python_module termcolor >= 2.4}
# /SECTION
Requires:       python-Flask >= 3.0
Requires:       python-Werkzeug >= 3.0
Requires:       python-paramiko >= 3.4
Requires:       python-termcolor >= 2.4
Requires(post): update-alternatives
Requires(postun): update-alternatives
BuildArch:      noarch
%python_subpackages

%description
storm manages the host entries in ~/.ssh/config: add, edit, update,
delete, list and search them from the command line, a local web UI,
or as a Python library.

%prep
%autosetup -p1 -n storm-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
%python_clone -a %{buildroot}%{_bindir}/storm
%python_expand %fdupes %{buildroot}%{$python_sitelib}

%check
# pyproject's addopts need pytest-cov, which is not a build requirement
%pytest -o addopts=""

%post
%python_install_alternative storm

%postun
%python_uninstall_alternative storm

%files %{python_files}
%license LICENSE
%doc README.md
%python_alternative %{_bindir}/storm
%{python_sitelib}/storm
%{python_sitelib}/stormssh-%{version}.dist-info

%changelog
