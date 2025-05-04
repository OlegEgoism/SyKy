🔌 BOO_SYS
- 🇧🇾 Приложение для заметок в системном трее 🇧🇾
 
🧾 Основные функции:
- Окно с текстовыми заметками
- Выбор цвета текста.

🎥 Видео-демо
Посмотрите, как OFF_RES работает на практике:
[![OFF_RES Видео-демо](https://img.youtube.com/vi/AVzxt623t2A/0.jpg)](https://www.youtube.com/watch?v=TDo2tV02jaE&ab)

-  ЗАПУСК В РЕЖИМИ РАЗАРБОТКИ.

💡 Установка apt для Debian/Ubuntu (основные библиотеки).
```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-appindicator3-0.1
```
Если буду проблемы добавить
```bash
sudo apt update
sudo apt install python3.10-dev
sudo apt install pkg-config
sudo apt install libcairo2-dev
sudo apt install build-essential
pip install pygobject
```

💡 Python-зависимости.
```bash
pip install -r requirements.txt
```

💡 Дополнительно (для GNOME Shell).
```bash
sudo apt install gnome-shell-extension-appindicator
```

💡 Запуск
```bash
python3 app.py
```

-  СБОРКА ПРИЛОЖЕНИЯ КАК УСТАНОВОЧНЫЙ ПАКЕТ.

💡 Запуск как пакет приложения
```bash
chmod +x build_deb.sh
./build_deb.sh
sudo dpkg -i deb_build/wor-sys.deb
```
💡 Сделай исполняемым:
```bash
chmod +x build_deb.sh
```

💡 Запуск
```bash
./build_deb.sh
```

💡 Установи пакет
```bash
sudo dpkg -i deb_build/wor-sys.deb
```

По вопросам писать на почту 📨: olegpustovalov220@gmail.com 