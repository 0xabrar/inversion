from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout

from kivy.config import Config
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.lang import Builder

from kivy.clock import Clock
from kivy.graphics import Rectangle, Color
from kivy.graphics.vertex_instructions import Line

from kivy.properties import BooleanProperty
from kivy.properties import StringProperty
from kivy.properties import NumericProperty

from commission import Commission
from omission import Omission
from archive import Archive
from stats import Stats

from database.db_function import *
from database.db_model import build_database

import json
from nltk.tag import pos_tag
import os.path

import random
import datetime

Builder.load_file('kv-files/commission.kv')
Builder.load_file('kv-files/omission.kv')
Builder.load_file('kv-files/archive.kv')
Builder.load_file('kv-files/stats.kv')

KIVY_FONTS = [
    {
        "name": "RobotoCondensed",
        "fn_regular": "fonts/RobotoCondensed-Light.ttf",
        "fn_bold": "fonts/RobotoCondensed-Regular.ttf",
        "fn_italic": "fonts/RobotoCondensed-LightItalic.ttf",
        "fn_bolditalic": "fonts/RobotoCondensed-Italic.ttf"
    }, {
        "name": "Ubuntu",
        "fn_regular": "fonts/Ubuntu-R.ttf",
        "fn_bold": "fonts/Ubuntu-B.ttf",
        "fn_italic": "fonts/Ubuntu-RI.ttf",
    }, {
        "name": "Quicksand",
        "fn_regular": "fonts/Quicksand-Regular.otf",
        "fn_bold": "fonts/Quicksand-Bold.otf",
        "fn_italic": "fonts/Quicksand-Italic.otf",
    }, {
        "name": "BebasNeue",
        "fn_regular": "fonts/BebasNeue-Regular.otf",
        "fn_bold": "fonts/BebasNeue-Bold.otf",
    }, {
        "name": "SourceSansPro",
        "fn_regular": "fonts/SourceSansPro-Regular.otf",
        "fn_bold": "fonts/SourceSansPro-Bold.otf",
    }, {
        "name": "OstrichSans",
        "fn_regular": "fonts/OstrichSans-Regular.ttf",
        "fn_bold": "fonts/OstrichSans-Bold.otf",
    }
]

for font in KIVY_FONTS:
    LabelBase.register(**font)

class JournalInterfaceManager(BoxLayout):

    def __init__(self, **kwargs):

        super(JournalInterfaceManager, self).__init__(**kwargs)
        self.windows = {}
        self.current_window = None

        # initially load the journal window as main window
        journal_menu = Journal()
        self.add_window("home", journal_menu)
        self.load_window("home")
        self.windows['home'].get_top_mistakes()

        omission = Omission()
        self.add_window("omission", omission)

        commission = Commission()
        self.add_window("commission", commission)

        archive = Archive()
        self.add_window("archive", archive)

        stats = Stats()
        self.add_window("stats", stats)

    def add_window(self, key, window):
        self.windows[key] = window

    def load_window(self, key):
        if key == 'commission':
            self.windows[key].display_mistakes()
            self.current_window = 'commission'
        elif key == 'omission':
            self.windows[key].display_mistakes()
            self.current_window = 'omission'
        elif key == 'home':
            self.windows[key].calculate_day_cost()
            self.current_window = 'home'
        elif key == 'archive':
            self.windows[key].order_by_time()
            self.current_window = 'archive'
        elif key == 'stats':
            self.current_windiw = 'stats'

        self.clear_widgets()
        self.add_widget(self.windows[key])

    def animate_circle(self, *args):
        if self.current_window == 'home':
            self.windows['home'].animate_circle()

    def change_top_mistake(self, *args):
        if self.current_window == 'home':
            self.windows['home'].change_top_mistake()

class MenuCanvas(BoxLayout):

    def __init__(self, **kwargs):
        super(MenuCanvas, self).__init__(**kwargs)

class Journal(BoxLayout):

    # angles used to keep track of circle arc
    start_angle = NumericProperty()
    end_angle = NumericProperty()

    def __init__(self, **kwargs):
        super(Journal, self).__init__(**kwargs)
        self.score_canvas = self.ids['menu_canvas'].canvas
        self.start_angle = 250
        self.end_angle = 360
        self.calculate_day_cost()
        self.top_nouns= []
        self.get_top_mistakes()

    def animate_circle(self, *args):
        self.start_angle = self.start_angle + 2.5 
        self.end_angle = self.end_angle + 2.5

    def get_top_nouns(self, top_nouns):
        pass

    def get_top_mistakes(self):
        '''Update the top mistakes stored on the main page.'''
    
        nouns = self.get_mistake_nouns()
        counts = self.get_nouns_count(nouns)
        top_nouns = [["", 0, 0], ["",0, 0], ["", 0, 0]]
        time = None
        old_list = {}
        changes = False
        if os.path.isfile("nouns.csv"):
            with open('nouns.csv', 'r') as in_file:
                time = datetime.datetime.strptime(in_file.readline().strip(),
                 "%Y-%m-%d %H:%M:%S.%f")
            
                for line in in_file:
                    temp = line.strip("\n").split(",")
                    old_list[temp[0]] = (int(temp[1]), float(temp[2]))
        else:
            changes = True

        # get top nouns from all nouns
        for noun, times in counts.items():
            if noun in old_list:
                if (times[0] != old_list[noun][0]):
                    temp = old_list.pop(noun)
                    temp = (times[0], temp[1]+1)
                    old_list[noun] = temp
                    changes = True
            else:
                old_list[noun] = (times[0], times[0]*times[1])
                changes = True

        for noun, times in old_list.items():
            if times[1] > top_nouns[2][1]:
                top_nouns.append([noun, times[1], times[0]]) 
                top_nouns.sort(key=lambda x: x[1], reverse=True)
                top_nouns.pop()

        self.update_mistake_changes(top_nouns, time, old_list)
        self.write_mistake_changes(changes, time, old_list)

    def update_mistake_changes(self, top_nouns, time, old_list):
        ''' Updates the values stored in top nouns with the new ones. '''
        for noun in top_nouns:
            mistakes_id = get_mistakes_with_keyword(noun[0])
            if time:
                if (time.date() != datetime.datetime.today().date()):
                    temp = old_list.pop(noun[0])
                    temp = (temp[0], temp[1]-0.2)
                    old_list[noun[0]] = temp
            for id in mistakes_id:
                mistake = get_mistake_verb(id) + " " + get_mistake_noun(id)
                self.top_nouns.append(mistake)

    def write_mistake_changes(self, changes, time, old_list):
        ''' Outputs the top mistakes into a file nouns.csv. '''
        if changes or (time.date() != datetime.datetime.today().date()):
            out_file = open("nouns.csv", "w")
            if (time != None):
                if (time.date() == datetime.datetime.today().date()):
                    out_file.write(str(time)+"\n")
                else:
                    out_file.write(str(datetime.datetime.today())+"\n")
            else:
                out_file.write(str(datetime.datetime.today())+"\n")
            for noun, times in old_list.items():
                out_file.write(str(noun)+","+str(times[0])+","+str(times[1])+"\n")
            out_file.close()

    def create_initial_json(self):
        nouns = self.get_mistake_nouns()
        counts = self.get_nouns_count(nouns)
        with open('mistakes.json', 'w') as data_file:
            json.dump(counts, data_file)

    def change_top_mistake(self):
        if not self.top_nouns:
            self.ids['mistakes'].text= 'You currently haven\'t made enough mistakes.'
        else:
            self.ids['mistakes'].text = random.choice(self.top_nouns)

    def get_nouns_count(self, nouns):
        counts = {}
        for noun in nouns:
            if noun in counts:
                counts[noun][0] += 1
            else:
                counts[noun] = [1, 1]
        return counts

    def get_mistake_nouns(self):
        mistakes_id = get_all_mistakes_id()
        for id in mistakes_id:
            phrase = get_mistake_noun(id)
            tagged_sent = pos_tag(phrase.split())
            nouns = [word for word, pos in tagged_sent if pos[0] == 'N']
            for noun in nouns:
                yield noun.strip('.')

    def calculate_day_cost(self):
        todays_eid = get_entry()
        todays_cost = 0

        if todays_eid is not None:
            mistakes_ids = get_entry_mistakes_id(todays_eid)
            for id in mistakes_ids:
                todays_cost += get_mistake_cost(id)

        self.ids['menu_canvas'].children[0].text = '$' + str(todays_cost)


class JournalApp(App):

    def build(self):
        build_database()
        self.journal = JournalInterfaceManager()
        Clock.schedule_interval(self.journal.animate_circle, 1/60.)
        Clock.schedule_interval(self.journal.change_top_mistake, 3)
        return self.journal 

    def load_window(self, key):
        self.journal.load_window(key)

if __name__ == "__main__":

    Window.size = (600, 850)
    LabelBase.register(name='Modern Pictograms', fn_regular='images/modernpics.ttf')
    JournalApp().run()
