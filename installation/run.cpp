#include <iostream>

int main() {
    system("start http://127.0.0.1:5000");
    //installer 
    system(
    "installation\\venvFriendlyFruit\\Scripts\\activate.bat &&"
    "python flask_mapbox\\server.py"
    );
    return 0;
}
