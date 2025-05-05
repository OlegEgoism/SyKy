import gi
import os
import json
import signal

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk, AppIndicator3, Gdk

NOTES_FILE = os.path.join(os.path.expanduser("~"), ".tray_notes.json")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".tray_notes_settings.json")
APP_ID = "boo_sys"
ICON_PATH = os.path.join(os.path.dirname(__file__), "logo.png")

notes_info = "Заметки"
settings_info = "Настройки"
notes_save = "Сохранить в файл"
exit_app = "Выход"


class NotesWindow(Gtk.Window):
    def __init__(self, app):
        super().__init__(title=notes_info)
        self.set_default_size(400, 300)
        self.set_border_width(4)
        self.app = app

        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()
        self.load_notes()

        # Контейнер для прокрутки и кнопки
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        scroll = Gtk.ScrolledWindow()
        scroll.add(self.textview)
        vbox.pack_start(scroll, True, True, 0)

        save_button = Gtk.Button(label=notes_save)
        save_button.connect("clicked", self.save_to_txt)
        vbox.pack_start(save_button, False, False, 0)

        self.connect("delete-event", self.on_close)

        self.apply_text_color()

    def load_notes(self):
        if os.path.exists(NOTES_FILE):
            try:
                with open(NOTES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.textbuffer.set_text(data.get("notes", ""))
            except Exception as e:
                print("Ошибка при загрузке заметок:", e)

    def save_notes(self):
        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_end_iter()
        text = self.textbuffer.get_text(start_iter, end_iter, True)

        try:
            with open(NOTES_FILE, "w", encoding="utf-8") as f:
                json.dump({"notes": text}, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print("Ошибка при сохранении заметок:", e)

    def save_to_txt(self, _button):
        dialog = Gtk.FileChooserDialog(
            title="Сохранить заметки как...",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )

        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )

        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name("note.txt")

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            start_iter = self.textbuffer.get_start_iter()
            end_iter = self.textbuffer.get_end_iter()
            text = self.textbuffer.get_text(start_iter, end_iter, True)

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"Заметки сохранены в: {file_path}")
            except Exception as e:
                print("Ошибка при сохранении файла:", e)

        dialog.destroy()

    def on_close(self, *args):
        self.save_notes()
        self.hide()
        return True

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def apply_text_color(self):
        settings = self.load_settings()
        color_str = settings.get("text_color")
        if color_str:
            css_provider = Gtk.CssProvider()
            css = f"""
            textview text {{
                color: {color_str};
            }}
            """
            try:
                css_provider.load_from_data(css.encode())
                Gtk.StyleContext.add_provider_for_screen(
                    Gdk.Screen.get_default(),
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
            except Exception as e:
                print("Ошибка применения стиля:", e)


class NotesTrayApp:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            APP_ID,
            ICON_PATH,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        self.menu = Gtk.Menu()

        self.open_item = Gtk.MenuItem(label=notes_info)
        self.open_item.connect("activate", self.open_notes)
        self.menu.append(self.open_item)

        self.settings_item = Gtk.MenuItem(label=settings_info)
        self.settings_item.connect("activate", self.open_settings)
        self.menu.append(self.settings_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.quit_item = Gtk.MenuItem(label=exit_app)
        self.quit_item.connect("activate", self.quit)
        self.menu.append(self.quit_item)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        self.window = NotesWindow(self)

    def open_notes(self, _):
        self.window.show_all()
        self.window.present()

    def open_settings(self, _):
        dialog = Gtk.ColorChooserDialog(title="Цвет текста", parent=self.window)

        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "text_color" in data:
                    rgba = Gdk.RGBA()
                    if rgba.parse(data["text_color"]):
                        dialog.set_rgba(rgba)
        except Exception:
            pass

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            color = dialog.get_rgba()
            color_str = color.to_string()
            try:
                with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                    json.dump({"text_color": color_str}, f, indent=4)
                self.window.apply_text_color()
            except Exception as e:
                print("Ошибка сохранения цвета:", e)

        dialog.destroy()

    def quit(self, _):
        self.window.save_notes()
        Gtk.main_quit()

    def run(self):
        Gtk.main()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = NotesTrayApp()
    app.run()
