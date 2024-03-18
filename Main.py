import sys
import pgdb
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import QObject, Qt

# Constantes para los datos codificados
BD_NOMBRE = "biblioteca"
BD_DIRECCION = "localhost"
BD_PUERTO = "5432"


def redimensionar_y_centrar_widget(widget, ancho, alto):
    tamano = widget.screen().size()
    pantalla_ancho = tamano.width()
    pantalla_alto = tamano.height()
    widget.setGeometry(
        pantalla_ancho / 2 - ancho / 2, pantalla_alto / 2 - alto / 2, ancho, alto
    )


class VentanaLogin(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Biblioteca Universidad Tecnológica")
        self.layout = QVBoxLayout()

        self.usuario_edit = QLineEdit()
        self.contrasena_edit = QLineEdit()
        self.contrasena_edit.setEchoMode(QLineEdit.Password)

        self.boton_inicio = QPushButton("Iniciar sesión")
        self.boton_inicio.clicked.connect(self.iniciar_sesion)

        self.etiqueta_info = QLabel("No deberia de verse esto")
        self.etiqueta_info.setVisible(False)

        self.layout.addWidget(QLabel("Usuario:"))
        self.layout.addWidget(self.usuario_edit)
        self.layout.addWidget(QLabel("Contraseña:"))
        self.layout.addWidget(self.contrasena_edit)
        self.layout.addWidget(self.etiqueta_info)
        self.layout.addWidget(self.boton_inicio)

        self.setWindowIcon(QIcon("icon.png"))
        redimensionar_y_centrar_widget(self, 260, 130)

        self.setLayout(self.layout)
        self.usuario_edit.setFocus()

    def iniciar_sesion(self):
        usuario = self.usuario_edit.text()
        contrasena = self.contrasena_edit.text()
        self.etiqueta_info.setText("Iniciando sesión...")
        self.etiqueta_info.setVisible(True)
        try:
            self.conn = pgdb.connect(
                dbname=BD_NOMBRE,
                user=usuario,
                password=contrasena,
                host=BD_DIRECCION,
                port=BD_PUERTO,
            )
            self.accept()
        except pgdb.InternalError as e:
            print("Error:", e)
            self.etiqueta_info.setText("Error al conectar: Verifica las credenciales.")
        except pgdb.Error as e:
            print("Error:", e)
            self.etiqueta_info.setText(
                "Error interno: Revisa la consola para más detalles."
            )


class VentanaPrincipal(QMainWindow):
    def __init__(self, conexion_db):
        super().__init__()
        self.setWindowTitle("Biblioteca Universidad Tecnológica")
        self.conexion_db = conexion_db

        self.widget_central = QLabel("")
        self.setCentralWidget(self.widget_central)
        self.setWindowIcon(QIcon("icon.png"))
        redimensionar_y_centrar_widget(self, 500, 400)

        # Establecer la imagen de fondo
        self.widget_central.setStyleSheet(
            """
            background-image: url(background.jpg);
            background-repeat: no-repeat;
            background-position: center;
            """
        )

        self.crear_menus()

    def crear_accion(
        self, texto: str, padre: QObject, atajo: str, tip: str, funcion=None
    ) -> QAction:
        accion = QAction(texto, padre)
        if atajo:
            accion.setShortcut(atajo)
        if tip:
            accion.setStatusTip(tip)
        if funcion:
            accion.triggered.connect(funcion)

        return accion

    def crear_menus(self):
        # Create a menubar
        barra_menus = self.menuBar()

        # File menu
        menu_archivo = barra_menus.addMenu("&Alumnos")

        # Create actions
        new_action = self.crear_accion(
            "&Nuevo registro",
            self,
            "Ctrl+N",
            "Registra un nuevo alumno",
            self.mostrar_alta,
        )
        menu_archivo.addAction(new_action)

        open_action = self.crear_accion(
            "&Abrir registro", self, "Ctrl+O", "Abre un registro de alumno existente"
        )
        menu_archivo.addAction(open_action)

        save_action = self.crear_accion(
            "&Guardar registros", self, "Ctrl+S", "Guarda los registros"
        )
        # save_action.triggered.connect(self.save_file)
        menu_archivo.addAction(save_action)

        menu_archivo.addSeparator()
        exit_action = self.crear_accion(
            "&Salir", self, "Ctrl+Q", "Sale de la aplicación", self.close
        )
        menu_archivo.addAction(exit_action)

    def ejecutar_consulta(self, consulta):
        try:
            cursor = self.conexion_db.cursor()
            cursor.execute(consulta)
            resultado = cursor.fetchall()
            cursor.close()

            # Mostrar el resultado en el widget de texto
            self.widget_central.clear()
            for fila in resultado:
                self.widget_central.append(str(fila))
        except pgdb.Error as e:
            print("Error:", e)

    def mostrar_alta(self):
        alta = DialogoAlta(self)
        if alta.exec() == QDialog.Accepted:
            pass


class DialogoAlta(QDialog):
    def __init__(self, padre):
        super().__init__()
        self.setWindowTitle("Alta de alumnos - Biblioteca Universidad Tecnológica")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Dialog)
        self.layout = QVBoxLayout()

        redimensionar_y_centrar_widget(self, 350, 150)

        self.padre = padre
        self.controles = {}

        self.layout.addWidget(QLabel("Codigo:"))
        self.controles["codigo"] = QLineEdit()
        self.layout.addWidget(self.controles["codigo"])

        self.layout.addWidget(QLabel("Nombre:"))
        self.controles["nombre"] = QLineEdit()
        self.layout.addWidget(self.controles["nombre"])

        self.layout.addWidget(QLabel("Carrera:"))
        self.controles["carrera"] = QLineEdit()
        self.layout.addWidget(self.controles["carrera"])

        self.layout.addWidget(QLabel("Correo:"))
        self.controles["correo"] = QLineEdit()
        self.layout.addWidget(self.controles["correo"])

        self.boton_inicio = QPushButton("Añadir alumno")
        # self.boton_inicio.clicked.connect(self.iniciar_sesion)
        self.layout.addWidget(self.boton_inicio)

        self.etiqueta_info = QLabel("No deberia de verse esto")
        self.etiqueta_info.setVisible(False)
        self.layout.addWidget(self.etiqueta_info)

        self.setLayout(self.layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    ventana_login = VentanaLogin()
    if ventana_login.exec() == QDialog.Accepted:
        conexion_db = ventana_login.conn
        ventana_principal = VentanaPrincipal(conexion_db)

        ventana_principal.show()
        sys.exit(app.exec())
