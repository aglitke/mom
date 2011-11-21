%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

Name:           mom
Version:        0.2.1
Release:        6%{?dist}
Summary:        Dynamically manage system resources on virtualization hosts

Group:          Applications/System
License:        GPLv2
URL:            http://wiki.github.com/aglitke/mom
Source0:        http://github.com/downloads/aglitke/mom/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  python-devel

# MOM makes use of libvirt by way of the python bindings to monitor and
# interact with virtual machines.
Requires:       libvirt, libvirt-python

Requires(post): chkconfig
Requires(postun): initscripts
Requires(preun): chkconfig
Requires(preun): initscripts

%description
MOM is a policy-driven tool that can be used to manage overcommitment on KVM 
hosts. Using libvirt, MOM keeps track of active virtual machines on a host. At 
a regular collection interval, data is gathered about the host and guests. Data 
can come from multiple sources (eg. the /proc interface, libvirt API calls, a 
client program connected to a guest, etc). Once collected, the data is 
organized for use by the policy evaluation engine. When started, MOM accepts a 
user-supplied overcommitment policy. This policy is regularly evaluated using 
the latest collected data. In response to certain conditions, the policy may 
trigger reconfiguration of the system’s overcommitment mechanisms. Currently 
MOM supports control of memory ballooning and KSM but the architecture is 
designed to accommodate new mechanisms such as cgroups.



%prep
%setup -q

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT
install -Dp contrib/momd.init $RPM_BUILD_ROOT/%{_initrddir}/momd

cp $RPM_BUILD_ROOT/%{_defaultdocdir}/%{name}/examples/mom-balloon+ksm.conf \
   $RPM_BUILD_ROOT/%{_sysconfdir}/momd.conf

# Correct the installed location of documentation files
mv $RPM_BUILD_ROOT/%{_defaultdocdir}/%{name} \
   $RPM_BUILD_ROOT/%{_defaultdocdir}/%{name}-%{version}
cp LICENSE README $RPM_BUILD_ROOT/%{_defaultdocdir}/%{name}-%{version}


%clean
rm -rf $RPM_BUILD_ROOT


%post
/sbin/chkconfig --add momd


%preun
if [ $1 = 0 ] ; then
    /sbin/service momd stop >/dev/null 2>&1
    /sbin/chkconfig --del momd
fi


%postun
if [ "$1" -ge "1" ] ; then
    /sbin/service momd condrestart >/dev/null 2>&1 || :
fi


%files
%defattr(-,root,root,-)
%{_sbindir}/momd
%{_initrddir}/momd
%{python_sitelib}/*
%config(noreplace) %{_sysconfdir}/momd.conf

# The use of '_defaultdocdir' conflicts with 'doc'. Therefore, 'doc' MUST NOT
# be used to include additional documentation files so long as this is in use.
%{_defaultdocdir}/%{name}-%{version}/


%changelog
* Mon Nov 21 2011 Adam Litke <agl@us.ibm.com> - 0.2.1-6
- Merge out-of-tree patches into mom

* Fri Jan 7 2011 Adam Litke <agl@us.ibm.com> - 0.2.1-5
- Address review comments by Michael Schwendt
- Fix use of _defaultdocdir macro
- Add some comments to the spec file

* Tue Oct 26 2010 Adam Litke <agl@us.ibm.com> - 0.2.1-4
- Third round of package review comments
- Remove useless shebang on non-executable python script

* Tue Oct 26 2010 Adam Litke <agl@us.ibm.com> - 0.2.1-3
- Second round of package review comments
- Add a default config file: /etc/momd.conf

* Wed Oct 13 2010 Adam Litke <agl@us.ibm.com> - 0.2.1-2
- Address initial package review comments

* Mon Sep 27 2010 Adam Litke <agl@us.ibm.com> - 0.2.1-1
- Initial package
