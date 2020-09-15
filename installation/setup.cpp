#include <iostream>
#include <windows.h>


int main() {
    // Python 3.7.1
    system("installation\\python-3.7.1rc2-amd64.exe");
    //C++ VC 2015,2017,2019
    system("installation\\VC_redist.x64.exe");
    //environnement virtuel
    system("python -m venv installation\\venvFriendlyFruit &&"
    "installation\\venvFriendlyFruit\\Scripts\\activate.bat &&"
    "pip install -r installation\\requirements.txt --build installation\\build &&"
    "pip install installation\\GDAL-3.1.2-cp37-cp37m-win_amd64.whl");
    return 0;
}