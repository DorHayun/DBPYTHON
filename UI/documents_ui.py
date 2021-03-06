import functools
from enum import Enum, auto
from sqlite3 import OperationalError

import PySimpleGUI as sg

import UI.UI_defaults as sgh
from BL.Documents_db import DocumentDatabase
from BL.exceptions import IntegrityError
from BL.xml.export_db import export_db
from BL.xml.import_db import import_db
from UI.UI_defaults import WINDOW_SIZE
from UI.headers.document_header import DocumentHeader
from UI.headers.custom_header import CustomHeader
from UI.headers.group_header import GroupHeader
from UI.headers.phrase_header import PhraseHeader
from UI.headers.statistics_header import StatisticsHeader
from UI.headers.word_header import WordHeader


class DocumentsUi:
    UNSAVED_DATA_WARNING = "Continuing will delete all unsaved data.\n" \
                           "Do you wish to continue?\n"

    AUTO_SAVE_NOTICE = "Please Notice:\n" \
                       "All feature work will be saved to this file automatically."

    RELOAD_ERROR = "An error accrued trying to load the database.\n" \
                   "Resetting..."

    INTEGRITY_ERROR = "Integrity error accrued.\n" \
                      "Corrupted XML."

    INVALID_XML_ERROR = "Invalid XML file.\n\n" \
                        "Error:\n"

    SAVE_SUCCESS = "Successfully saved a copy of the current work."

    LOADING_SUCCESS = "Successfully loaded from file."

    TAB_CLASSES = StatisticsHeader, DocumentHeader, WordHeader, GroupHeader, PhraseHeader

    # Event keys
    class KEYS(Enum):
        UPLOAD_BUTTON = auto()
        SAVE_BUTTON = auto()
        IMPORT_BUTTON = auto()
        EXPORT_BUTTON = auto()
        TABS = auto()

    def __init__(self):
        sgh.config_theme()

        self.db = DocumentDatabase()

        self.window = sg.Window(sgh.WINDOW_TITLE, size=WINDOW_SIZE, finalize=True)
        self.tabs = sg.TabGroup([self.create_tabs()], key=DocumentsUi.KEYS.TABS, enable_events=True)
        self.window.layout([
            self._create_menu_buttons_row(),
            [self.tabs]
        ])
        self.window.finalize()
        self.window.TKroot.bind('<Return>', self.handle_enter)

        self.callbacks = {
            DocumentsUi.KEYS.UPLOAD_BUTTON: self._load_database,
            DocumentsUi.KEYS.SAVE_BUTTON: functools.partial(self._save_database, True),
            DocumentsUi.KEYS.IMPORT_BUTTON: self.import_database,
            DocumentsUi.KEYS.EXPORT_BUTTON: self._export_database
        }

    @staticmethod
    def _create_menu_buttons_row():

        upload_button = sg.Button(
            button_text="Upload",
            key=DocumentsUi.KEYS.UPLOAD_BUTTON
        )

        save_button = sg.Button(
            button_text="Save",
            key=DocumentsUi.KEYS.SAVE_BUTTON
        )

        import_button = sg.Button(
            button_text="Import",
            key=DocumentsUi.KEYS.IMPORT_BUTTON
        )

        export_button = sg.Button(
            button_text="Export",
            key=DocumentsUi.KEYS.EXPORT_BUTTON
        )

        return [upload_button, save_button, import_button, export_button]

    def _reload_tabs(self):
        try:
            for row in self.tabs.Rows:
                for tab in row:
                    tab.reload()
        except OperationalError:
            sg.popup_yes_no(self.RELOAD_ERROR, title="Error")
            self.reset_database(ask_for_confirmation=False)
            return False

        return True

    def reset_database(self, ask_for_confirmation=True):
        if not ask_for_confirmation or sg.popup_yes_no(self.UNSAVED_DATA_WARNING, title="New") == "Yes":
            self.db.new_connection()
            self._reload_tabs()

    def _save_database(self, switch_to_new):
        path = sg.popup_get_file(
            message=None,
            no_window=True,
            save_as=True,
            file_types=(("Database", "*.BL"), ("ALL Files", "*.*"))
        )

        if path:
            self.db.save_to_file(path, switch_to_new)

            if switch_to_new:
                sg.popup_ok(DocumentsUi.AUTO_SAVE_NOTICE, title="Save", non_blocking=True)
            else:
                sg.popup_ok(self.SAVE_SUCCESS, title="Saved As", non_blocking=True)

    def _load_database(self):
        if sg.popup_yes_no(self.UNSAVED_DATA_WARNING, title="Load") == "Yes":
            path = sg.PopupGetFile(
                message=None,
                no_window=True,
                file_types=(("Database", "*.BL"), ("ALL Files", "*.*"))
            )

            if path:
                self.db.new_connection(new_path=path)
                if self._reload_tabs():
                    sg.popup_ok(self.LOADING_SUCCESS, DocumentsUi.AUTO_SAVE_NOTICE, title="Load", non_blocking=True)

    def _export_database(self):
        path = sg.popup_get_file(
            message=None,
            no_window=True,
            save_as=True,
            file_types=(("XML", "*.xml"), ("ALL Files", "*.*"))
        )

        if path:
            export_db(self.db, path)

    def import_database(self):
        if sg.popup_yes_no(self.UNSAVED_DATA_WARNING, title="Import") == "Yes":
            path = sg.PopupGetFile(
                message=None,
                no_window=True,
                file_types=(("XML", "*.xml"), ("ALL Files", "*.*"))
            )

            if path:
                try:
                    import_db(self.db, path)
                    self._reload_tabs()
                except ValueError as e:
                    sg.popup_ok(self.INVALID_XML_ERROR + str(e), title="Import")
                except IntegrityError:
                    sg.popup_ok(self.INTEGRITY_ERROR, title="Import")
                    self.reset_database(ask_for_confirmation=False)

    def create_tabs(self):
        return [tab_class(self.db) for tab_class in DocumentsUi.TAB_CLASSES]

    def initialize_tabs(self):
        for row in self.tabs.Rows:
            for tab in row:
                tab.initialize()

    def handle_enter(self, _key_event):
        curr_tab = self.window.Element(self.tabs.get())  # type: CustomHeader
        curr_tab.handle_enter(self.window.find_element_with_focus())

    def debug_init_db(self):
        self.db.insert_words_group("Test")
        self.db.insert_words_group("Test Words")

    def start(self):
        self.initialize_tabs()

        while True:
            event = self.window.read()[0]

            if event is None:
                break
            elif event in self.callbacks:
                self.callbacks[event]()
            else:
                curr_tab = self.window.Element(self.tabs.get())  # type: CustomHeader
                curr_tab.handle_event(event)

        self.db.commit()
        self.window.close()
