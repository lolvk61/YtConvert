"""Dark media workspace with native multimedia playback."""
import os
from pathlib import Path
from functools import partial
from queue import SimpleQueue, Empty
from threading import Thread
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / ".deps"))
from PySide6.QtCore import Qt, QUrl, QTimer, QVariantAnimation, QEasingCurve, QRectF
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QFileDialog,
    QMessageBox, QSlider, QFrame, QProgressBar)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
import media

VIDEO = ["MP4", "MKV", "WEBM", "MOV", "AVI"]
AUDIO = ["MP3", "WAV", "M4A", "FLAC", "OGG", "OPUS", "AAC"]
TOOLS = [
    ("download", "↓   Скачать", "Скачивание с YouTube"),
    ("convert", "↻   Конвертировать", "Конвертация видео"),
    ("extract", "♫   Извлечь звук", "Видео в аудио"),
    ("gif", "▧   Создать GIF", "Видео в GIF"),
    ("video", "✂   Обрезать видео", "Обрезка видео"),
    ("audio", "♫   Обрезать звук", "Обрезка аудио"),
]
STYLE = """
QWidget {color:#e9edf8; font:11pt 'Segoe UI';}
QMainWindow, QWidget#workspace {background:#0c101a;}
QFrame#sidebar {background:#101623; border-right:1px solid #202a3b;}
QLabel {background:transparent;}
QLabel#brand {font-size:19pt; font-weight:700; color:#eff5ff;}
QLabel#title {font-size:27pt; font-weight:700; letter-spacing:-1px;}
QLabel#muted {color:#8d9bb4; font-size:10pt;}
QLabel#empty {background:#111a29; border:1px solid #26354b; border-radius:18px; color:#8b9fbe; font-size:15pt;}
QLineEdit,QComboBox {background:#151e2e; color:#e7efff; border:1px solid #2c3a51; border-radius:10px; padding:12px; selection-background-color:#356b96;}
QLineEdit:focus,QComboBox:focus {border:1px solid #69c6dc;}
QComboBox::drop-down {border:0; width:26px;}
QComboBox QAbstractItemView {background:#172235; color:#e9edf8; selection-background-color:#2c526d; padding:6px;}
QSlider::groove:horizontal {height:5px; background:#26354a; border-radius:2px;}
QSlider::sub-page:horizontal {background:#65d5d3; border-radius:2px;}
QSlider::handle:horizontal {background:#c1ffff; width:14px; margin:-5px 0; border-radius:7px;}
QProgressBar {border:0; background:#1d2b40; max-height:4px; border-radius:2px;}
QProgressBar::chunk {background:#65d5d3;}
QToolTip {background:#202e44; color:white; border:0; padding:8px;}
QMessageBox,QFileDialog {background:#151e2e;}
"""


class FlowButton(QPushButton):
    """Paint a moving highlight while preserving QPushButton interaction."""
    def __init__(self, text):
        super().__init__(text)
        self.hover_amount = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self.setStyleSheet("padding:10px 18px; border:0; background:transparent;")
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(380)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.valueChanged.connect(self.animate)

    def animate(self, value):
        self.hover_amount = float(value)
        self.update()

    def transition(self, target):
        self.animation.stop()
        self.animation.setStartValue(self.hover_amount)
        self.animation.setEndValue(target)
        self.animation.start()

    def enterEvent(self, event):
        if self.isEnabled():
            self.transition(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.transition(0.0)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1,1,-1,-1)
        primary = self.objectName() == "primary"
        active = self.isChecked()
        gradient = QLinearGradient(0,0,self.width(),self.height())
        if primary:
            gradient.setColorAt(0,QColor("#77e3cd"))
            gradient.setColorAt(1,QColor("#65a7f0"))
            foreground = QColor("#0c2436")
        elif active:
            gradient.setColorAt(0,QColor("#244858"))
            gradient.setColorAt(1,QColor("#22364f"))
            foreground = QColor("#aef8ef")
        else:
            gradient.setColorAt(0,QColor("#1c2a3e"))
            gradient.setColorAt(1,QColor("#172131"))
            foreground = QColor("#dee9fc")
        painter.setOpacity(1 if self.isEnabled() else .4)
        painter.setPen(QPen(QColor("#3b596f") if active else QColor("#2a3a50"),1))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect,11,11)
        if self.hover_amount > 0 and self.isEnabled():
            shimmer = QLinearGradient(-self.width()+self.width()*2*self.hover_amount,0,
                                       self.width()*2*self.hover_amount,self.height())
            shimmer.setColorAt(0,QColor(150,230,255,0))
            shimmer.setColorAt(.5,QColor(180,240,255,65))
            shimmer.setColorAt(1,QColor(150,230,255,0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(shimmer)
            painter.drawRoundedRect(rect,11,11)
        if self.isDown():
            painter.setBrush(QColor(0,0,0,35))
            painter.drawRoundedRect(rect,11,11)
        if self.hasFocus():
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#a7eeff"),1.5))
            painter.drawRoundedRect(rect.adjusted(2,2,-2,-2),9,9)
        painter.setPen(foreground)
        font = self.font()
        font.setBold(primary or active)
        painter.setFont(font)
        painter.drawText(rect,Qt.AlignCenter,self.text())

class Studio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YtConvert")
        self.setWindowIcon(QIcon(str(media.ROOT / "assets" / "app.ico")))
        self.resize(1180, 870)
        self.setMinimumSize(1060, 820)
        self.busy = False
        self.output = None
        self.events = SimpleQueue()
        self.preview_end = None
        self.player = QMediaPlayer(self)
        self.sound = QAudioOutput(self)
        self.sound.setVolume(.7)
        self.player.setAudioOutput(self.sound)
        host = QWidget()
        host.setObjectName("workspace")
        self.setCentralWidget(host)
        layout = QHBoxLayout(host)
        layout.setContentsMargins(0,0,0,0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        navigation = QVBoxLayout(sidebar)
        navigation.setContentsMargins(18,30,18,24)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(media.ROOT / "assets" / "app.png")).scaled(
            64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        navigation.addWidget(logo)
        brand = QLabel("YtConvert")
        brand.setObjectName("brand")
        navigation.addWidget(brand)
        navigation.addWidget(QLabel("Личная студия медиа"))
        navigation.addSpacing(32)
        navigation.setSpacing(10)
        self.buttons = []
        for mode, label, title in TOOLS:
            button = FlowButton(label)
            button.setCheckable(True)
            button.clicked.connect(partial(self.show_tool, mode, title))
            navigation.addWidget(button)
            self.buttons.append((mode,button))
        navigation.addStretch()
        note = QLabel("ВИДЕО · АУДИО · GIF")
        note.setObjectName("muted")
        navigation.addWidget(note)
        layout.addWidget(sidebar)
        content = QVBoxLayout()
        content.setContentsMargins(36,32,36,28)
        content.setSpacing(12)
        layout.addLayout(content,1)
        self.title = QLabel()
        self.title.setObjectName("title")
        content.addWidget(self.title)
        subtitle = QLabel("Выберите источник, настройте результат и сохраните файл")
        subtitle.setObjectName("muted")
        content.addWidget(subtitle)
        row = QHBoxLayout()
        self.source = QLineEdit()
        self.browse = FlowButton("Открыть файл")
        self.browse.clicked.connect(self.choose)
        row.addWidget(self.source,1)
        row.addWidget(self.browse)
        content.addLayout(row)
        self.video = QVideoWidget()
        self.video.setMinimumHeight(180)
        self.player.setVideoOutput(self.video)
        content.addWidget(self.video,1)
        self.empty = QLabel("Откройте файл для предпросмотра")
        self.empty.setObjectName("empty")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setMinimumHeight(200)
        content.addWidget(self.empty,1)
        self.playback = QWidget()
        controls = QVBoxLayout(self.playback)
        controls.setContentsMargins(0,0,0,0)
        self.seek = QSlider(Qt.Horizontal)
        self.seek.sliderMoved.connect(self.seek_to)
        controls.addWidget(self.seek)
        row = QHBoxLayout()
        self.play = FlowButton("▶  Пуск")
        self.play.clicked.connect(self.toggle)
        self.play.setMinimumWidth(110)
        row.addWidget(self.play)
        self.fragment = FlowButton("▶  Фрагмент")
        self.fragment.clicked.connect(self.play_fragment)
        row.addWidget(self.fragment)
        self.clock = QLabel("0:00 / 0:00")
        row.addWidget(self.clock)
        row.addStretch()
        volume = QSlider(Qt.Horizontal)
        volume.setMaximumWidth(90)
        volume.setRange(0,100)
        volume.setValue(70)
        volume.valueChanged.connect(lambda v:self.sound.setVolume(v/100))
        row.addWidget(QLabel("Звук"))
        row.addWidget(volume)
        controls.addLayout(row)
        content.addWidget(self.playback)
        self.range_box = QWidget()
        row = QHBoxLayout(self.range_box)
        row.setContentsMargins(0,0,0,0)
        self.begin = QLineEdit("0")
        self.end = QLineEdit()
        self.end.setPlaceholderText("До конца")
        for label, field in (("Начало",self.begin),("Конец",self.end)):
            column = QVBoxLayout()
            column.addWidget(QLabel(label + " · секунды"))
            column.addWidget(field)
            mark = FlowButton("Установить по плееру")
            mark.clicked.connect(lambda checked=False, target=field:target.setText(f"{self.player.position()/1000:.3f}"))
            column.addWidget(mark)
            row.addLayout(column)
        content.addWidget(self.range_box)
        row = QHBoxLayout()
        self.format = QComboBox()
        self.quality = QComboBox()
        self.quality.addItems(["2160p","1440p","1080p","720p","480p","360p"])
        self.quality.setCurrentText("1080p")
        self.gif_width = QComboBox()
        self.gif_width.addItems(["320 px","480 px","640 px","960 px"])
        self.gif_width.setCurrentIndex(1)
        self.fps = QComboBox()
        self.fps.addItems(["8 fps","12 fps","15 fps","24 fps"])
        self.fps.setCurrentIndex(1)
        row.addWidget(QLabel("Результат"))
        for widget in (self.format,self.quality,self.gif_width,self.fps):
            row.addWidget(widget)
        row.addStretch()
        content.addLayout(row)
        self.status = QLabel("Готово к работе")
        self.status.setWordWrap(True)
        self.status.setObjectName("muted")
        content.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        content.addWidget(self.progress)
        row = QHBoxLayout()
        self.action = FlowButton("Сохранить результат")
        self.action.setObjectName("primary")
        self.action.clicked.connect(self.start)
        row.addWidget(self.action)
        self.reveal = FlowButton("Открыть папку")
        self.reveal.clicked.connect(self.open_folder)
        self.reveal.setEnabled(False)
        row.addWidget(self.reveal)
        row.addStretch()
        content.addLayout(row)
        self.player.durationChanged.connect(lambda duration:self.seek.setRange(0,duration))
        self.player.positionChanged.connect(self.position)
        self.player.playbackStateChanged.connect(lambda state:self.play.setText(
            "Ⅱ  Пауза" if state == QMediaPlayer.PlayingState else "▶  Пуск"))
        self.player.errorOccurred.connect(lambda error,message:self.status.setText("Предпросмотр: "+message))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(80)
        self.show_tool("download","Скачивание с YouTube")

    def show_tool(self, mode, title):
        self.player.stop()
        self.player.setSource(QUrl())
        self.preview_end = None
        self.mode = mode
        self.title.setText(title)
        for key, button in self.buttons:
            button.setChecked(key == mode)
        download = mode == "download"
        self.source.clear()
        self.source.setPlaceholderText("https://www.youtube.com/watch?v=…" if download else "Выберите медиафайл")
        self.source.setReadOnly(not download)
        self.browse.setVisible(not download)
        self.video.hide()
        self.empty.show()
        self.empty.setText("↓\nВставьте ссылку на видео YouTube\n\nВыберите формат и качество сохранения" if download else
                           "▷\nОткройте файл для предпросмотра\n\nПросматривайте видео и слушайте звук здесь")
        self.playback.setVisible(not download)
        self.range_box.setVisible(mode in {"video","audio","gif"})
        self.fragment.setVisible(mode in {"video","audio","gif"})
        self.begin.setText("0")
        self.end.clear()
        self.format.clear()
        self.format.addItems(VIDEO+AUDIO if download else AUDIO if mode in {"audio","extract"} else ["GIF"] if mode=="gif" else VIDEO)
        self.quality.setVisible(download)
        self.gif_width.setVisible(mode=="gif")
        self.fps.setVisible(mode=="gif")
        self.action.setText("Скачать" if download else "Сохранить результат")

    def choose(self):
        path,_ = QFileDialog.getOpenFileName(self,"Открыть медиафайл")
        if path:
            self.player.stop()
            self.preview_end = None
            self.source.setText(path)
            self.begin.setText("0")
            self.end.clear()
            self.empty.hide()
            self.video.show()
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.pause()

    def seek_to(self, position):
        self.preview_end = None
        self.player.setPosition(position)

    def toggle(self):
        self.preview_end = None
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def bounds(self):
        start = media.timestamp(self.begin.text())
        end = media.timestamp(self.end.text()) if self.end.text().strip() else None
        if end is not None and end <= start:
            raise ValueError("Конец должен быть позже начала.")
        return start,end

    def play_fragment(self):
        try:
            start,end = self.bounds()
            duration = self.player.duration()/1000
            if not duration or start >= duration or end is not None and end > duration+.05:
                raise ValueError("Выберите границы внутри длительности файла.")
            self.preview_end = round((end if end is not None else duration)*1000)
            self.player.setPosition(round(start*1000))
            self.player.play()
        except ValueError as error:
            QMessageBox.warning(self,"Границы",str(error))

    def position(self, value):
        if not self.seek.isSliderDown():
            self.seek.setValue(value)
        def stamp(ms):
            seconds = ms//1000
            return f"{seconds//60}:{seconds%60:02}"
        self.clock.setText(stamp(value)+" / "+stamp(self.player.duration()))
        if self.preview_end is not None and value >= self.preview_end:
            self.player.pause()
            self.preview_end = None

    def start(self):
        try:
            extension = self.format.currentText().lower()
            if self.mode == "download":
                url = media.youtube_url(self.source.text().strip())
                folder = QFileDialog.getExistingDirectory(self,"Папка сохранения")
                if not folder: return
                operation = partial(media.download,url,Path(folder),int(self.quality.currentText()[:-1]),extension=extension)
            else:
                source = Path(self.source.text())
                if not source.is_file(): raise ValueError("Выберите исходный файл.")
                start,end = self.bounds() if self.mode in {"video","audio","gif"} else (0,None)
                target,_ = QFileDialog.getSaveFileName(self,"Сохранить результат",
                    str(source.with_name(source.stem+"_result."+extension)),f"{extension.upper()} (*.{extension})")
                if not target: return
                target = Path(target)
                if target.suffix.lower() != "."+extension: target = Path(str(target)+"."+extension)
                if target.resolve() == source.resolve() or target.exists() and target.samefile(source):
                    raise ValueError("Выберите другое имя результата.")
                operation = partial(media.convert,"video" if self.mode=="convert" else self.mode,
                    source,target,start,end,int(self.fps.currentText().split()[0]),int(self.gif_width.currentText().split()[0]))
            self.busy = True
            self.player.pause()
            self.action.setEnabled(False)
            self.browse.setEnabled(False)
            for _,button in self.buttons: button.setEnabled(False)
            self.progress.setRange(0,0)
            self.status.setText("Подготовка…")
            Thread(target=self.work,args=(operation,),daemon=True).start()
        except (ValueError,OSError) as error:
            QMessageBox.warning(self,"Проверьте параметры",str(error))

    def work(self,operation):
        try:
            media.ensure_tools(lambda message:self.events.put(("status",message)))
            result = operation(lambda message:self.events.put(("status",message)))
            self.events.put(("done",result))
        except Exception as error:
            self.events.put(("error",str(error)))

    def poll(self):
        try:
            while True:
                kind,value = self.events.get_nowait()
                if kind == "status":
                    self.status.setText(value)
                    continue
                self.busy = False
                self.action.setEnabled(True)
                self.browse.setEnabled(True)
                for _,button in self.buttons: button.setEnabled(True)
                self.progress.setRange(0,100)
                self.progress.setValue(100 if kind=="done" else 0)
                if kind=="done":
                    self.output = value
                    self.status.setText("Сохранено · "+value.name)
                    self.reveal.setEnabled(True)
                else:
                    self.status.setText("Ошибка обработки")
                    QMessageBox.warning(self,"Ошибка",value)
        except Empty:
            pass

    def open_folder(self):
        if self.output:
            os.startfile(self.output.parent)

    def closeEvent(self,event):
        if self.busy:
            self.status.setText("Дождитесь завершения обработки.")
            event.ignore()
        else:
            self.player.stop()
            event.accept()

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from selftest import run_selftest
        sys.exit(run_selftest(sys.argv))
    app = QApplication(sys.argv)
    app.setApplicationName("YtConvert")
    app.setApplicationVersion("1.0.0")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = Studio()
    window.show()
    sys.exit(app.exec())
