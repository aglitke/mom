# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

Name:		mom           
Version:        0.2
Release:        1%{?dist}
Summary:        Dynamically manage system resources on virtualization hosts

Group:          Applications/System
License:        GPLv2
URL:            http://wiki.github.com/aglitke/mom
Source0:        http://github.com/downloads/aglitke/mom/mom-0.2.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires:  python-devel
Requires:	libvirt, libvirt-python

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


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --root $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/%_initddir
cp contrib/momd.init $RPM_BUILD_ROOT/%_initddir/momd


%clean
rm -rf $RPM_BUILD_ROOT


%post
# This adds the proper /etc/rc*.d links for the script
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
%(_bindir)/usr/sbin/momd
%_initddir/momd
%doc /usr/share/doc/mom/examples/*
%{python_sitelib}/*


%changelog
* Mon Sep 27 2010 Adam Litke <agl@us.ibm.com> - 0.2-1
- Initial package
