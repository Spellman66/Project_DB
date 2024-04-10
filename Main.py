import sys
import pgdb
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import QObject, Qt

# Constantes para los datos codificados
BD_NOMBRE = "biblioteca"
BD_DIRECCION = "localhost"
BD_PUERTO = "5432"


class Alumno:
    codigo: int
    nombre: str
    carrera: str
    correo: str

    def __init__(self, codigo: int, nombre: str, carrera: str, correo: str) -> None:
        self.codigo = codigo
        self.nombre = nombre
        self.carrera = carrera
        self.correo = correo


def redimensionar_y_centrar_widget(widget: QWidget, ancho: int, alto: int):
    tamano = widget.screen().size()
    pantalla_ancho = tamano.width()
    pantalla_alto = tamano.height()
    widget.setGeometry(
        (pantalla_ancho / 2) - (ancho / 2),
        (pantalla_alto / 2) - (alto / 2),
        ancho,
        alto,
    )


class VentanaInicioSesion(QDialog):
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
    def __init__(self, conexion_db: pgdb.connection.Connection):
        super().__init__()
        self.setWindowTitle("Biblioteca Universidad Tecnológica")
        self.conexion_db: pgdb.connection.Connection = conexion_db

        self.layout = QGridLayout()
        self.widget_central = QLabel("")
        self.widget_central.setLayout(self.layout)
        self.setCentralWidget(self.widget_central)
        self.setWindowIcon(QIcon("icon.png"))
        redimensionar_y_centrar_widget(self, 500, 400)

        self.tabla_alumnos = QTableWidget(self.widget_central)
        self.tabla_alumnos.setColumnCount(4)
        self.tabla_alumnos.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.tabla_alumnos.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_alumnos.setHorizontalHeaderLabels(
            ("Codigo", "Nombre", "Carrera", "Correo")
        )
        self.tabla_alumnos.verticalHeader().setVisible(False)
        self.tabla_alumnos.itemClicked.connect(self.actualizar_estado_menus)
        self.rellenar_tabla_alumnos()
        self.layout.addWidget(self.tabla_alumnos, 0, 0)

        # Establecer la imagen de fondo
        self.widget_central.setStyleSheet(
            """
            background-image: url(background.jpg);
            background-repeat: no-repeat;
            background-position: center;
            """
        )

        self.crear_menus()

    def actualizar_estado_menus(self):
        if self.tabla_alumnos.selectedItems():
            self.alumno_editar.setDisabled(False)
            self.alumno_borrar.setDisabled(False)
        else:
            self.alumno_editar.setDisabled(True)
            self.alumno_borrar.setDisabled(True)

    def rellenar_tabla_alumnos(self):
        self.tabla_alumnos.setRowCount(0)
        cursor = self.conexion_db.execute("SELECT * FROM alumno")
        alumnos = cursor.fetchall()

        if alumnos:
            self.tabla_alumnos.setRowCount(len(alumnos))
            for i, alumno in enumerate(alumnos):
                for j, atributo in enumerate(alumno):
                    self.tabla_alumnos.setItem(i, j, QTableWidgetItem(str(atributo)))

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
        self.barra_menus = self.menuBar()

        self.archivo_abrir = self.crear_accion(
            "&Abrir registro", self, "Ctrl+A", "Abre un registro de alumno existente"
        )
        self.archivo_guardar = self.crear_accion(
            "&Guardar registros", self, "Ctrl+G", "Guarda los registros"
        )
        self.archivo_salir = self.crear_accion(
            "&Salir", self, "Ctrl+Q", "Sale de la aplicación", self.close
        )

        # File menu
        self.menu_archivo = self.barra_menus.addMenu("&Archivo")
        self.menu_archivo.addAction(self.archivo_abrir)
        self.menu_archivo.addAction(self.archivo_guardar)
        self.menu_archivo.addSeparator()
        self.menu_archivo.addAction(self.archivo_salir)

        self.alumno_registrar = self.crear_accion(
            "&Nuevo alumno",
            self,
            "Ctrl+N",
            "Registra un nuevo alumno",
            self.nuevo_alumno,
        )
        self.alumno_editar = self.crear_accion(
            "&Editar alumno",
            self,
            "Ctrl+E",
            "Modifica la información de un alumno",
            self.editar_alumno,
        )
        self.alumno_editar.setDisabled(True)
        self.alumno_borrar = self.crear_accion(
            "&Borrar alumno",
            self,
            "Ctrl+B",
            "Elimina a un alumno del sistema",
            self.eliminar_alumno,
        )
        self.alumno_borrar.setDisabled(True)

        self.menu_archivo = self.barra_menus.addMenu("A&lumnos")
        self.menu_archivo.addAction(self.alumno_registrar)
        self.menu_archivo.addSeparator()
        self.menu_archivo.addAction(self.alumno_editar)
        self.menu_archivo.addSeparator()
        self.menu_archivo.addAction(self.alumno_borrar)

    def ejecutar_consulta(self, consulta):
        try:
            cursor = self.conexion_db.cursor()
            cursor.execute(consulta)
            resultado = cursor.fetchall()
            cursor.close()

            return resultado
        except pgdb.Error as e:
            print("Error:", e)

            return None

    def nuevo_alumno(self):
        alta = FormularioAlumno()
        if alta.exec() == QDialog.Accepted and alta.alumno:
            consulta = "INSERT INTO alumno (codigo, nombre, carrera, correo) VALUES (%d, %s, %s, %s);"
            alumno = alta.alumno
            self.conexion_db.execute(
                consulta, (alumno.codigo, alumno.nombre, alumno.carrera, alumno.correo)
            )
            self.conexion_db.commit()
            self.rellenar_tabla_alumnos()

    def editar_alumno(self):
        items = self.tabla_alumnos.selectedItems()
        alumno = Alumno(
            int(items[0].text()), items[1].text(), items[2].text(), items[3].text()
        )

        alta = FormularioAlumno(alumno)
        if alta.exec() == QDialog.Accepted and alta.alumno:
            consulta = "UPDATE alumno SET codigo=%d, nombre=%s, carrera=%s, correo=%s WHERE codigo=%d;"
            alumno = alta.alumno
            self.conexion_db.execute(
                consulta, (alumno.codigo, alumno.nombre, alumno.carrera, alumno.correo, alumno.codigo)
            )
            self.conexion_db.commit()
            self.rellenar_tabla_alumnos()

    def eliminar_alumno(self):
        items = self.tabla_alumnos.selectedItems()
        codigo = int(items[0].text())
        consulta = "DELETE FROM alumno WHERE codigo=%d"
        self.conexion_db.execute(consulta, (codigo,))
        self.conexion_db.commit()
        self.rellenar_tabla_alumnos()


class FormularioAlumno(QDialog):
    def __init__(self, alumno: Alumno = None):
        super().__init__()
        self.setWindowTitle("Alta de alumnos - Biblioteca Universidad Tecnológica")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Dialog)
        self.layout = QVBoxLayout()

        redimensionar_y_centrar_widget(self, 350, 150)

        self.alumno = alumno
        self.controles = {}

        self.layout.addWidget(QLabel("Codigo:"))
        self.codigo = QLineEdit()
        self.layout.addWidget(self.codigo)

        self.layout.addWidget(QLabel("Nombre:"))
        self.nombre = QLineEdit()
        self.layout.addWidget(self.nombre)

        self.layout.addWidget(QLabel("Carrera:"))
        self.carrera = QLineEdit()
        self.layout.addWidget(self.carrera)

        self.layout.addWidget(QLabel("Correo:"))
        self.correo = QLineEdit()
        self.layout.addWidget(self.correo)

        if self.alumno:
            self.codigo.setText(str(self.alumno.codigo))
            self.nombre.setText(self.alumno.nombre)
            self.carrera.setText(self.alumno.carrera)
            self.correo.setText(self.alumno.correo)

        self.boton_inicio = QPushButton("Añadir alumno")
        # self.boton_inicio.clicked.connect(self.iniciar_sesion)
        self.layout.addWidget(self.boton_inicio)
        self.boton_inicio.clicked.connect(self.registrar)

        self.etiqueta_info = QLabel("No deberia de verse esto")
        self.etiqueta_info.setVisible(False)
        self.layout.addWidget(self.etiqueta_info)

        self.setLayout(self.layout)

    def registrar(self):
        self.alumno = Alumno(
            int(self.codigo.text()),
            self.nombre.text(),
            self.carrera.text(),
            self.correo.text(),
        )
        self.accept()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    ventana_login = VentanaInicioSesion()
    if ventana_login.exec() == QDialog.Accepted:
        conexion_db = ventana_login.conn
        ventana_principal = VentanaPrincipal(conexion_db)

        ventana_principal.show()
        sys.exit(app.exec())
