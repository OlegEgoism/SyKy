import gi
import os
import json
import signal
import time
from threading import Thread
import pygame

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
clear_notes = "Очистить"
restore_notes = "Восстановить"
exit_app = "Выход"
timer_info = "Таймер"
start_timer = "Страт"
stop_timer = "Стоп"


class NotesWindow(Gtk.Window):
    def __init__(self, app):
        super().__init__(title=notes_info)
        self.set_default_size(400, 300)
        self.set_border_width(4)
        self.app = app
        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()
        self.load_notes()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.textview)
        vbox.pack_start(scroll, True, True, 0)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vbox.pack_start(hbox, False, False, 0)
        save_button = Gtk.Button(label=notes_save)
        save_button.connect("clicked", self.save_to_txt)
        hbox.pack_start(save_button, False, False, 0)
        clear_button = Gtk.Button(label=clear_notes)
        clear_button.connect("clicked", self.clear_notes)
        hbox.pack_start(clear_button, False, False, 0)
        restore_button = Gtk.Button(label=restore_notes)
        restore_button.connect("clicked", self.restore_notes)
        hbox.pack_start(restore_button, False, False, 0)
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

    def clear_notes(self, _button):
        self.textbuffer.set_text("")
        print("Заметки очищены.")

    def restore_notes(self, _button):
        self.load_notes()
        print("Заметки восстановлены.")

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


class TimerWindow(Gtk.Window):
    def __init__(self, app):
        super().__init__(title=timer_info)
        self.set_default_size(200, 100)
        self.set_border_width(4)
        self.app = app
        self.hours_entry = Gtk.Entry()
        self.hours_entry.set_placeholder_text("Часы")
        self.minutes_entry = Gtk.Entry()
        self.minutes_entry.set_placeholder_text("Минуты")
        self.seconds_entry = Gtk.Entry()
        self.seconds_entry.set_placeholder_text("Секунды")
        hbox_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        start_button = Gtk.Button(label=start_timer)
        start_button.connect("clicked", self.start_timer)
        hbox_buttons.pack_start(start_button, True, True, 0)
        stop_button = Gtk.Button(label=stop_timer)
        stop_button.connect("clicked", self.stop_timer)
        hbox_buttons.pack_start(stop_button, True, True, 0)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.pack_start(self.hours_entry, False, False, 0)
        vbox.pack_start(self.minutes_entry, False, False, 0)
        vbox.pack_start(self.seconds_entry, False, False, 0)
        vbox.pack_start(hbox_buttons, False, False, 0)
        self.add(vbox)
        self.timer_thread = None
        self.timer_running = False

    def start_timer(self, _):
        try:
            hours = int(self.hours_entry.get_text() or 0)
            minutes = int(self.minutes_entry.get_text() or 0)
            seconds = int(self.seconds_entry.get_text() or 0)
            total_seconds = hours * 3600 + minutes * 60 + seconds
            if total_seconds > 0:
                if not self.timer_running:
                    self.timer_running = True
                    self.timer_thread = Thread(target=self.run_timer, args=(total_seconds,))
                    self.timer_thread.start()
                    self.hide()
                else:
                    print("Таймер уже запущен!")
            else:
                print("Введите положительное количество времени.")
        except ValueError:
            print("Введите корректное число.")

    def stop_timer(self, _):
        if self.timer_running:
            self.timer_running = False
            if self.timer_thread:
                self.timer_thread.join()
            self.app.update_tray_label("")
            print("Таймер остановлен.")

    def run_timer(self, total_seconds):
        while total_seconds > 0 and self.timer_running:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            remaining_time = f"{hours:02}:{minutes:02}:{seconds:02}"
            self.app.update_tray_label(f"  Таймер: {remaining_time}")
            print(f"Осталось: {remaining_time}")
            time.sleep(1)
            total_seconds -= 1

        if self.timer_running:
            print("Таймер завершен!")
            self.timer_running = False
            self.app.update_tray_label("  Таймер завершен")
            self.show_notification()

    def show_notification(self):
        dialog = Gtk.MessageDialog(
            parent=self,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Таймер завершен!"
        )
        pygame.mixer.init()
        pygame.mixer.Sound("vo.mp3").play()  # Воспроизведение звука
        dialog.run()
        dialog.destroy()


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
        self.timer_item = Gtk.MenuItem(label=timer_info)
        self.timer_item.connect("activate", self.open_timer)
        self.menu.append(self.timer_item)
        self.settings_item = Gtk.MenuItem(label=settings_info)
        self.settings_item.connect("activate", self.open_settings)
        self.menu.append(self.settings_item)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.quit_item = Gtk.MenuItem(label=exit_app)
        self.quit_item.connect("activate", self.quit)
        self.menu.append(self.quit_item)
        self.menu.show_all()
        self.indicator.set_menu(self.menu)
        self.notes_window = NotesWindow(self)
        self.timer_window = TimerWindow(self)
        self.timer_window.app = self

    def open_settings(self, _):
        dialog = Gtk.ColorChooserDialog(title="Цвет текста", parent=self.notes_window)
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
                self.notes_window.apply_text_color()
            except Exception as e:
                print("Ошибка сохранения цвета:", e)

        dialog.destroy()

    def open_notes(self, _):
        self.notes_window.show_all()
        self.notes_window.present()

    def open_timer(self, _):
        self.timer_window.show_all()
        self.timer_window.present()

    def update_tray_label(self, text):
        self.indicator.set_label(text, "")

    def quit(self, _):
        self.notes_window.save_notes()
        Gtk.main_quit()

    def run(self):
        Gtk.main()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = NotesTrayApp()
    app.run()
