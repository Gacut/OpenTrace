# Qt/PySide6 source and relinking information

OpenTrace 1.0.0 uses the following unmodified LGPL components:

- Qt 6.11.1
- PySide6 6.11.1
- PySide6 Essentials 6.11.1
- PySide6 Addons 6.11.1
- Shiboken6 6.11.1

## Corresponding source

The corresponding upstream source archives are:

- Qt:
  `qt-everywhere-src-6.11.1.tar.xz`
- Qt for Python, including PySide6 and Shiboken6:
  `pyside-setup-everywhere-src-6.11.1.tar.xz`

For at least three years after an OpenTrace 1.0.0 binary was distributed,
any recipient may request a copy of the corresponding source code by opening
an issue at:

https://github.com/Gacut/OpenTrace/issues

The source will be supplied at no charge through a download controlled by the
OpenTrace distributor. If physical delivery is requested, only the reasonable
cost of the medium and delivery may be charged.

For reference, the original upstream archives are published at:

- https://download.qt.io/official_releases/qt/6.11/6.11.1/single/
- https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.1-src/

The written offer above does not depend on those upstream links remaining
available.

## Using a modified Qt/PySide6 build

OpenTrace is distributed as an `onedir` application. Qt and PySide6 remain
separate dynamic libraries in the application directory rather than being
statically linked into `OpenTrace.exe`.

The supported and safest way to test a modified library is to rebuild the
open-source OpenTrace application:

1. Install Python 3.12.
2. Build or install your compatible modified Qt for Python 6.11.1 package.
3. Create and activate a virtual environment.
4. Install OpenTrace without replacing your modified Qt for Python package.
5. Install PyInstaller 6.21.0.
6. Run `pyinstaller --clean --noconfirm opentrace.spec`.
7. Start `dist/OpenTrace/OpenTrace.exe`.

It is also possible to replace the matching dynamic Qt/PySide6 libraries in
the `onedir` distribution. All mutually dependent files must remain
ABI-compatible and come from the same build.

The OpenTrace license does not prohibit reverse engineering performed for
debugging modifications to LGPL-covered libraries. No signature check, DRM,
or hardware restriction is used to prevent a recipient from running a
compatible modified library.
