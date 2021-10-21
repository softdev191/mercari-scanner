import sys
from PyQt5 import QtGui
from PyQt5.QtCore import QThread
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QTextBrowser, QComboBox, QHBoxLayout, QVBoxLayout, QTableWidgetItem, QTableWidget, QDialog, QDoubleSpinBox
from PyQt5.QtGui import QPixmap
from tutorial.spiders.search_spider import SearchSpider
from twisted.internet import reactor
from scrapy.crawler import CrawlerRunner
from multiprocessing import Process, Manager, freeze_support
from datetime import datetime
from scrapy.crawler import CrawlerProcess
import json
from urllib.request import urlopen

def crawl(Q, keyword, oldItems, firstScan):
  # CrawlerProcess
  process = CrawlerProcess()

  process.crawl(SearchSpider, Q=Q, keyword=keyword, oldItems=oldItems, firstScan=firstScan)
  process.start()

class UI(QWidget):
  dlgs = []
  def __init__(self):
    super(UI, self).__init__()
    self.setWindowTitle('Scrapy')
    self.keyword_line = QLineEdit(self)
    self.speed_line = QDoubleSpinBox(self)
    self.speed_line.setDecimals(1)
    self.speed_line.setRange(0, 100)
    self.speed_line.setSingleStep(0.5)
    self.crawl_btn = QPushButton('Start', self)
    self.h_layout = QHBoxLayout()
    self.h_layout2 = QHBoxLayout()
    self.log_browser = QTextBrowser(self)

    self.lbl_keyword = QLabel('Keyword')
    self.lbl_speed = QLabel('Speed')
    self.lbl_keyword.setFixedWidth(50)
    self.lbl_speed.setFixedWidth(50)

    self.h_layout.addWidget(self.lbl_keyword)
    self.h_layout.addWidget(self.keyword_line)
    self.h_layout2.addWidget(self.lbl_speed)
    self.h_layout2.addWidget(self.speed_line)
    self.v_layout = QVBoxLayout()
    self.v_layout.addLayout(self.h_layout)
    self.v_layout.addLayout(self.h_layout2)
    self.v_layout.addWidget(self.log_browser, 1)
    self.v_layout.addWidget(self.crawl_btn)
    self.setLayout(self.v_layout)
    self.resize(400, 300)

    self.Q = Manager().Queue()
    self.log_thread = LogThread(self)
    self.crawl_btn.clicked.connect(self.crawl_slot)
    self.log_thread.showDialog.connect(self.show_popup)

    self.dlgs = []
  def closeEvent(self, event):
    print('closed')
    self.p.terminate()
    self.log_thread.terminate()
    for dlg in self.dlgs:
      dlg.close()
    event.accept()
  def show_popup(self, obj):
    dlg = QDialog()
    self.dlgs.append(dlg)
    dlg.setWindowTitle("Dialog")
    dlg.setWindowModality(Qt.NonModal)

    v_layout = QVBoxLayout()
    v_layout.addWidget(QLabel(obj['name'],dlg))
    v_layout.addWidget(QLabel('出品者:{}'.format(obj['seller']),dlg))
    image_link = 'https://static.mercdn.net/item/detail/orig/photos/m14589631013_1.jpg?1629104664'
    for item in self.log_thread.oldItems:
      if item['link'] == obj['link']:
        image_link = item['image']
    print(image_link)
    url_data = urlopen(image_link).read()
    pixmap = QPixmap()
    pixmap.loadFromData(url_data)
    lbl = QLabel('', dlg)
    lbl.setPixmap(pixmap.scaled(200, 200))
    v_layout.addWidget(lbl)
    h_layout = QHBoxLayout()
    h_layout.addWidget(QLabel('価格'))
    h_layout.addWidget(QLabel(obj['price']))
    v_layout.addLayout(h_layout)
    dlg.setLayout(v_layout)
    dlg.move(20 * (len(self.dlgs) % 20 + 1), 20 * (len(self.dlgs) % 20 + 1))
    dlg.resize(220, 220)
    dlg.show()
  def crawl_slot(self):
    if (self.crawl_btn.text() == 'Start'):
      self.crawl_btn.setText('Stop')
      self.log_thread.start()
      self.start_process(oldItems=[], firstScan=True)
    else:
      self.crawl_btn.setText('Start')
      self.p.terminate()
      self.log_thread.terminate()
      now = datetime.now()
      current_time = now.strftime("%H:%M:%S")
      self.log_browser.append('Service Finished {}\n'.format(current_time))
  def start_process(self, oldItems, firstScan):
    keyword = self.keyword_line.text().strip()
    self.p = Process(target=crawl, args=(self.Q, keyword, oldItems, firstScan))
    self.p.start()
class LogThread(QThread):
    firstScan = True
    oldItems = []
    showDialog = pyqtSignal(dict)
    def __init__(self, gui):
      super(LogThread, self).__init__()
      self.gui = gui
    def run(self):
      while True:
        if not self.gui.Q.empty():
          pr = self.gui.Q.get()
          now = datetime.now()
          current_time = now.strftime("%H:%M:%S")
          if pr == 'Start':
            self.gui.log_browser.append('Service Started {}\n'.format(current_time))
          elif pr == 'Stop':
            self.gui.log_browser.append('Service Stopped {}\n'.format(current_time))
            sleepm = self.gui.speed_line.value() * 1000
            if (sleepm > 0):
              self.msleep(int(sleepm))
            self.gui.start_process(self.oldItems, False)
          elif pr == 'Scrapped':
            self.gui.log_browser.append('Scrapped {}\n'.format(current_time))
            self.firstScan = False
          else:
            obj = json.loads(pr)
            if obj['type'] == 'list':
              if self.firstScan == True:
                self.oldItems.append(obj)
              else:
                exist = False
                for oi in self.oldItems:
                  if oi['link'] == obj['link']:
                    exist = True
                if exist != True:
                  self.oldItems.append(obj)
            elif obj['type'] == 'item':
              print(obj)
              self.showDialog.emit(obj)
              self.msleep(500)
          self.gui.log_browser.moveCursor(QtGui.QTextCursor.End)
          self.msleep(10)
if __name__ == '__main__':
  freeze_support()
  app = QApplication(sys.argv)
  ui = UI()
  ui.show()
  sys.exit(app.exec_())