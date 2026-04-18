# SPEC для установки GUI, PyInstaller-демона, KIO и ярлыка приложения.
# См. packaging/rpm/README.md — бинарники должны лежать в SOURCES.

%global debug_package %{nil}

Name:           cloudfusion
Version:        0.1.0
Release:        1%{?dist}
Summary:        CloudFusion - cloud disk and Dolphin integration
License:        MIT
URL:            https://github.com/FunDuckich/disco-hack
Source0:        cloudfusion
Source1:        cloudfusion-daemon
Source2:        share_bridge.py
Source3:        cloudfusion-link.desktop
Source4:        cloudfusion-app.desktop

BuildArch:      x86_64

# FUSE для pyfuse3 в демоне; на части дистрибутивов пакет называется libfuse3 — при необходимости добавьте в Requires.
Requires:       fuse3
# libnotify optional for share_bridge (kdialog fallback); omit Recommends for older rpmbuild.

%description
CloudFusion: демон FastAPI (PyInstaller), нативное приложение Tauri, пункт сервисного меню Dolphin
для публикации публичной ссылки на файл.

%prep
# Нет исходников для распаковки — всё из Sources.

%build
# Бинарники уже собраны.

%install
install -d %{buildroot}%{_bindir}
install -d %{buildroot}%{_libexecdir}/cloudfusion
install -d %{buildroot}%{_datadir}/applications
install -d %{buildroot}%{_datadir}/kio/servicemenus

install -m0755 %{SOURCE0} %{buildroot}%{_bindir}/cloudfusion
install -m0755 %{SOURCE1} %{buildroot}%{_libexecdir}/cloudfusion/cloudfusion-daemon
install -m0755 %{SOURCE2} %{buildroot}%{_libexecdir}/cloudfusion/share_bridge.py

# KIO: подставляем путь к мосту (как в integration/desktop/install-user.sh).
sed 's|REPLACE_CF_SHARE_BRIDGE|%{_libexecdir}/cloudfusion/share_bridge.py|' \
  %{SOURCE3} > %{buildroot}%{_datadir}/kio/servicemenus/cloudfusion-link.desktop
chmod 0644 %{buildroot}%{_datadir}/kio/servicemenus/cloudfusion-link.desktop

install -m0644 %{SOURCE4} %{buildroot}%{_datadir}/applications/cloudfusion-app.desktop

%post
echo "CloudFusion установлен. Перезапустите Dolphin, чтобы появился пункт меню KIO (kquitapp5 dolphin && dolphin)."

%files
%{_bindir}/cloudfusion
%{_libexecdir}/cloudfusion/cloudfusion-daemon
%{_libexecdir}/cloudfusion/share_bridge.py
%{_datadir}/kio/servicemenus/cloudfusion-link.desktop
%{_datadir}/applications/cloudfusion-app.desktop

%changelog
* Sat Apr 18 2026 CloudFusion Packaging <packaging@local> - 0.1.0-1
- Initial spec: Tauri, daemon, KIO, desktop files.
