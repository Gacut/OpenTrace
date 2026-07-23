# Third-party licenses

OpenTrace 1.0.0 is licensed under the MIT License. Its Windows distribution
also contains the following third-party components.

## Qt for Python

- PySide6 6.11.1
- PySide6 Essentials 6.11.1
- PySide6 Addons 6.11.1
- Shiboken6 6.11.1
- Qt 6.11.1 libraries collected by PyInstaller
- License: GNU Lesser General Public License version 3 (LGPL-3.0-only), with
  GPL and commercial alternatives offered by the copyright holders
- Copyright: The Qt Company Ltd. and other Qt Project contributors
- Project: https://doc.qt.io/qtforpython-6/

OpenTrace uses the LGPL option. The Qt libraries are distributed as separate
dynamic libraries and have not been modified by the OpenTrace project.
Recipients may replace or modify these libraries and may reverse engineer
OpenTrace when necessary to debug such modifications, as permitted by
LGPL-3.0.

The complete LGPL text is included in `licenses/LGPL-3.0.txt`. Because LGPLv3
incorporates terms from GPLv3, `licenses/GPL-3.0.txt` is included as well.
Information about obtaining the corresponding library source code and
rebuilding OpenTrace with a modified library is in
`licenses/QT_SOURCE_AND_RELINKING.md`.

Qt and Qt for Python contain additional third-party components. Their notices
are shipped inside the corresponding Qt/PySide6 distribution and are
documented at:
https://doc.qt.io/qtforpython-6/licenses.html

## Python

- Python 3.12
- License: Python Software Foundation License
- Project: https://www.python.org/
- License text: `licenses/PYTHON-LICENSE.txt`

Python is bundled into the standalone Windows build by PyInstaller.

## PyInstaller

- PyInstaller 6.21.0
- License: GPL-2.0-or-later with a special exception permitting distribution
  of bundled applications
- Project: https://pyinstaller.org/
- License text and exception: `licenses/PYINSTALLER-LICENSE.txt`

PyInstaller is a build tool. Its bootloader is present in the standalone
executable; PyInstaller does not impose the GPL on OpenTrace due to the
exception stated in its license.

## Development-only dependencies

The following packages are used to develop and test OpenTrace and are not
intended to be bundled into the application:

- pytest: MIT License
- pytest-qt: MIT License
- setuptools: MIT License

The copyright notices and license metadata delivered with those packages
remain applicable.
