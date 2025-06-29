import os
import json
import hmac
import hashlib
import cairo
import gi
import tempfile
import xdg.BaseDirectory
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from language import LANGUAGES, LANGUAGES_DEFAULT

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, GLib, AppIndicator3, Notify

TZ = ZoneInfo("Europe/Minsk")
CONFIG_DIR = os.path.expanduser("~/.config/code_generator")
CONFIG_PATH = os.path.join(CONFIG_DIR, "secret.json")
APPEND = "OLEG"  # <-- Секретный ключ для (можете установить свой)
INTERVAL = 30  # <-- Время обновления сгенерированного ключа
SIZE_KODE = 6  # <-- Длина сгенерированного ключа


def get_temp_dir():
    """Возвращает правильный временный каталог в зависимости от окружения"""
    if 'SNAP' in os.environ:
        snap_tmp = os.path.join(os.environ['SNAP_USER_DATA'], 'tmp')
        os.makedirs(snap_tmp, exist_ok=True)
        return snap_tmp
    cache_dir = os.path.join(xdg.BaseDirectory.xdg_cache_home, 'code_generator')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


class TrayApp:
    def __init__(self):
        self.last_secret = ""
        self.last_code = "—"
        self.time_left = INTERVAL
        self.notifications_enabled = True
        self.code_visible = True
        self.default_icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "logo.png"))
        self.current_icon_path = self.default_icon_path
        self.language = LANGUAGES_DEFAULT
        self.previous_icon_paths = set()

        Notify.init(LANGUAGES.get(self.language, {}).get("app_name", "Code Generator"))
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.load_config()

        self.ind = AppIndicator3.Indicator.new(
            "code-generator",
            self.default_icon_path,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.create_menu()

        GLib.timeout_add_seconds(1, self.tick)

    def cleanup(self):
        """Очистка временных файлов"""
        temp_dir = get_temp_dir()
        if not os.path.exists(temp_dir):
            return

        current_files = set(os.listdir(temp_dir))
        for filename in current_files:
            full_path = os.path.join(temp_dir, filename)
            if (full_path != self.current_icon_path and
                    filename.startswith('code_gen_') and
                    filename.endswith('.png')):
                try:
                    os.unlink(full_path)
                except Exception as e:
                    print(f"Error removing old icon {filename}: {e}")

    def tr(self, key):
        return LANGUAGES.get(self.language, {}).get(key, key) or key

    def load_config(self):
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_secret = data.get("secret", "")
                    self.notifications_enabled = data.get("notifications_enabled", True)
                    self.code_visible = data.get("code_visible", True)
                    self.language = data.get("language", LANGUAGES_DEFAULT)
        except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "secret": self.last_secret,
                    "notifications_enabled": self.notifications_enabled,
                    "code_visible": self.code_visible,
                    "language": self.language
                }, f, ensure_ascii=False, indent=2)
        except (IOError, PermissionError) as e:
            print(f"Error saving config: {e}")

    def create_menu(self):
        menu = Gtk.Menu()

        self.code_item = Gtk.MenuItem(label=self._code_label())
        self.code_item.set_sensitive(False)
        menu.append(self.code_item)
        menu.append(Gtk.SeparatorMenuItem())

        set_key = Gtk.MenuItem(label=self.tr("word_key"))
        set_key.connect("activate", self.on_input)
        menu.append(set_key)
        menu.append(Gtk.SeparatorMenuItem())

        self.notify_toggle = Gtk.CheckMenuItem(label=self.tr("notifications"))
        self.notify_toggle.set_active(self.notifications_enabled)
        self.notify_toggle.connect("toggled", self.on_toggle_notifications)
        menu.append(self.notify_toggle)

        toggle_code_item = Gtk.CheckMenuItem(label=self.tr("display"))
        toggle_code_item.set_active(self.code_visible)
        toggle_code_item.connect("toggled", self.on_toggle_code_visibility)
        menu.append(toggle_code_item)
        menu.append(Gtk.SeparatorMenuItem())

        lang_menu = Gtk.Menu()
        lang_item = Gtk.MenuItem(label=self.tr("language"))
        lang_item.set_submenu(lang_menu)

        en_item = Gtk.RadioMenuItem(label="English")
        ru_item = Gtk.RadioMenuItem(label="Русский", group=en_item)
        de_item = Gtk.RadioMenuItem(label="Deutsch", group=en_item)
        zh_item = Gtk.RadioMenuItem(label="中文", group=en_item)

        lang_items = {
            "ru": ru_item,
            "en": en_item,
            "de": de_item,
            "zh": zh_item
        }

        lang_items.get(self.language, en_item).set_active(True)

        for code, item in lang_items.items():
            item.connect("activate", self.on_language_change, code)
            lang_menu.append(item)

        menu.append(lang_item)
        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label=self.tr("quit"))
        quit_item.connect("activate", self.on_quit)
        menu.append(quit_item)

        menu.show_all()
        self.ind.set_menu(menu)

    def on_quit(self, _):
        """Обработчик выхода из приложения"""
        self.cleanup()
        Gtk.main_quit()

    def _code_label(self):
        return self.tr("code_label").format(code=self.last_code, time_left=self.time_left)

    def on_toggle_notifications(self, widget):
        if widget:
            self.notifications_enabled = widget.get_active()
            self.save_config()

    def on_toggle_code_visibility(self, widget):
        if widget:
            self.code_visible = widget.get_active()
            self.update_code(force=True)
            self.save_config()

    def on_language_change(self, widget, language_code):
        if widget and language_code and self.language != language_code:
            self.language = language_code
            self.save_config()
            self.create_menu()
            Notify.uninit()
            Notify.init(self.tr("app_name"))
            self.update_code(force=True)

    def on_input(self, _):
        dialog = Gtk.Dialog(title=self.tr("set_key_title"))
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        entry = Gtk.Entry()
        entry.set_text(self.last_secret)
        dialog.get_content_area().add(entry)
        dialog.show_all()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            secret = entry.get_text().strip()
            if secret and secret != self.last_secret:
                self.last_secret = secret
                self.save_config()
                self.update_code(force=True)
        dialog.destroy()

    def tick(self):
        if not self.last_secret:
            return True
        self.update_code()
        return True

    def update_code(self, force=False):
        now = datetime.now(TZ)
        t_sec = int(now.astimezone(timezone.utc).timestamp())
        self.time_left = INTERVAL - (t_sec % INTERVAL)
        code = self.generate_code(self.last_secret)
        changed = (code != self.last_code)
        self.last_code = code
        self.code_item.set_label(self._code_label())

        if self.code_visible:
            self.ind.set_label(f" {self.last_code}", "")
        else:
            self.ind.set_label("", "")

        self.update_icon()

        if (changed and not force or force) and self.notifications_enabled:
            self.show_notification(code)

    def generate_code(self, secret, digits=SIZE_KODE):
        if not secret:
            return "0" * digits

        now = datetime.now(TZ)
        slot = int(now.astimezone(timezone.utc).timestamp()) // INTERVAL
        msg = f"{secret}:{APPEND}:{slot}".encode()
        hm = hmac.new(secret.encode(), msg, hashlib.sha256).digest()
        return f"{int.from_bytes(hm[:4], 'big') % (10 ** digits):0{digits}d}"

    def show_notification(self, code):
        if not self.notifications_enabled or not code:
            return
        try:
            title = self.tr("code_updated").format(code=code)
            notification = Notify.Notification.new(title, icon=self.default_icon_path)
            notification.show()
        except Exception as e:
            print(f"Error showing notification: {e}")

    def update_icon(self):
        try:
            temp_dir = get_temp_dir()
            os.makedirs(temp_dir, exist_ok=True)

            with tempfile.NamedTemporaryFile(
                    prefix='code_gen_',
                    suffix='.png',
                    dir=temp_dir,
                    delete=False
            ) as tmp_file:
                icon_path = tmp_file.name

            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 64, 64)
            context = cairo.Context(surface)
            context.set_source_rgba(0, 0, 0, 0)
            context.paint()
            context.arc(32, 32, 28, 0, 2 * 3.14159)
            context.set_source_rgba(0.7, 0.7, 0.7, 0.3)
            context.fill()
            progress = 1 - (self.time_left / INTERVAL)
            context.arc(32, 32, 28, -0.5 * 3.14159, (progress * 2 * 3.14159) - 0.5 * 3.14159)
            context.line_to(32, 32)
            context.set_source_rgba(0.0, 0.6, 0.0, 0.7)
            context.fill()
            context.arc(32, 32, 28, 0, 2 * 3.14159)
            context.set_line_width(2)
            context.set_source_rgba(0.4, 0.4, 0.4, 0.7)
            context.stroke()

            if os.path.exists(self.default_icon_path):
                try:
                    app_icon_surface = cairo.ImageSurface.create_from_png(self.default_icon_path)
                    context.set_source_surface(app_icon_surface, 16, 16)
                    context.paint()
                except Exception as e:
                    print(f"Error loading app icon: {e}")

            surface.write_to_png(icon_path)
            self.ind.set_icon_full(icon_path, self.tr("app_name"))

            if hasattr(self, 'current_icon_path') and self.current_icon_path != icon_path:
                if (self.current_icon_path != self.default_icon_path and
                        os.path.exists(self.current_icon_path)):
                    try:
                        os.unlink(self.current_icon_path)
                    except Exception as e:
                        print(f"Error removing old icon: {e}")
                self.current_icon_path = icon_path

            surface.finish()
        except Exception as e:
            print(f"Error updating icon: {e}")
            self.ind.set_icon_full(self.default_icon_path, self.tr("app_name"))


def main():
    try:
        app = TrayApp()
        Gtk.main()
    except Exception as e:
        print(f"Application error: {e}")
        raise


if __name__ == "__main__":
    main()
