# pip3 install PySide6, pygresql, yagmail, reportlab
# 
# Equipo 1 - Bases de datos D02
# 
# ** Eder **
# ** Edson **
# ** Isaac **
# ** Cristopher **
# 
# Programa de biblioteca

from __future__ import annotations

import sys
import hashlib
import pathlib
import pgdb

import yagmail

from datetime import datetime, timedelta
from typing import Any, NamedTuple, Iterable
from collections import namedtuple
from abc import ABC

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QPushButton,
    QLabel,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLineEdit,
    QInputDialog,
)
from PySide6.QtGui import QAction, QIcon, QDesktopServices
from PySide6.QtCore import QObject, Qt, QUrl


Columna = namedtuple("Columna", ("columna", "tipo"))

# Constantes
BD_NOMBRE = "biblioteca"
BD_DIRECCION = "localhost"
BD_PUERTO = "5432"
BD_USUARIO = ""
BD_CLAVE = ""
FORMATO_FECHA = "%Y-%m-%d"
NIVEL_ADMINISTRADOR = 0
NIVEL_EMPLEADO = 1
NUM_DIAS_PRESTAMO = 7
COSTO_DIA_PENALIZACION = 5
USUARIO_GMAIL = ""
CLAVE_GMAIL = ""

# Cadenas
TEXTO_ADICION_CORRECTA = "Se ha añadido al %s correctamente"
TEXTO_ADICION_FALLIDA = "No se pudo añadir al %s"
TEXTO_EDICION_CORRECTA = "Se ha modificado al %s correctamente"
TEXTO_EDICION_FALLIDA = "No se pudo modificar al %s"
TEXTO_BORRADO_CORRECTO = "Se ha eliminado al %s correctamente"
TEXTO_BORRADO_FALLIDO = "No se pudo eliminar al %s"
TEXTO_ASUNTO_RECORDATORIO_PRESTAMO = (
    "Recordatorio: próxima fecha de devolución de libro"
)
TEXTO_ASUNTO_SOLICITUD_PRESTAMO = "Confirmación de solicitud de préstamo de libro"
TEXTO_CONTENIDO_SOLICITUD_PRESTAMO = """
Estimado {},

Es un placer informarte que tu solicitud de préstamo de libro ha sido procesada con éxito en la Biblioteca de la Universidad Tecnológica. A continuación, encontrarás los detalles de tu préstamo:

- Folio del préstamo: {}
- Título del libro: {}
- Autor: {}
- Año de publicación: {}
- ISBN: {}
- Número de ejemplar: {}
- Fecha de solicitud: {}
- Fecha de devolución: {}

Recuerda que la fecha de devolución acordada es crucial para evitar penalizaciones. Te recordamos que, según nuestras políticas, existe una penalización de $5 por cada día de retraso en la devolución del libro después de la fecha acordada.

Por favor, asegúrate de devolver el libro en o antes de la fecha de devolución para evitar cargos adicionales.

Si tienes alguna pregunta o necesitas más asistencia, no dudes en ponerte en contacto con nosotros.

Gracias por utilizar nuestros servicios bibliotecarios.

Saludos cordiales,
Biblioteca de la Universidad Tecnológica
"""
TEXTO_CONTENIDO_RECORDATORIO_PRESTAMO = """
Estimado {},

Esperamos que este correo te encuentre bien. Queremos recordarte que la fecha de devolución del libro que solicitaste está próxima. A continuación, se detallan los datos pertinentes:

- Folio del prestamo: {}
- Título del libro: {}
- Fecha de devolución acordada: {}

Según nuestros registros, el libro debe ser devuelto en o antes de la fecha mencionada anteriormente para evitar cargos por retraso. Te recordamos que, de acuerdo con nuestras políticas, existe una penalización de $5 pesos por cada día de retraso en la devolución del libro después de la fecha acordada.

Por favor, asegúrate de devolver el libro a la biblioteca antes de la fecha de devolución para evitar cargos adicionales.

Si necesitas extender el plazo de préstamo o tienes alguna pregunta, no dudes en comunicarte con nosotros lo antes posible.

Gracias por tu cooperación y comprensión.

Atentamente,
Biblioteca de la Universidad Tecnológica
"""
try:
    _conexion = pgdb.connect(
        dbname=BD_NOMBRE,
        user=BD_USUARIO,
        password=BD_CLAVE,
        host=BD_DIRECCION,
        port=BD_PUERTO,
    )
except pgdb.Error as e:
    print(f"No se pudo conectar con la base de datos. Detalles:\n{e}")
    exit()


def main():
    app = QApplication(sys.argv)

    ventana_login = VentanaInicioSesion()
    if ventana_login.exec() == QDialog.DialogCode.Accepted:
        ventana_principal = VentanaPrincipal(ventana_login.usuario.nivel)

        ventana_principal.show()
        sys.exit(app.exec())


def redimensionar_y_centrar_widget(widget: QWidget, ancho: int, alto: int):
    tamano = widget.screen().size()
    pantalla_ancho = tamano.width()
    pantalla_alto = tamano.height()
    widget.setGeometry(
        (pantalla_ancho // 2) - (ancho // 2),
        (pantalla_alto // 2) - (alto // 2),
        ancho,
        alto,
    )


Usuario = namedtuple("Usuario", ["nombre", "hash", "nivel"])
Alumno = namedtuple("Alumno", ["codigo", "nombre", "carrera", "correo"])
Profesor = namedtuple("Profesor", ["codigo", "nombre", "carrera", "correo"])
Libro = namedtuple(
    "Libro",
    [
        "isbn",
        "titulo",
        "autor",
        "editorial",
        "aniopublicacion",
        "ejemplar",
        "disponible",
    ],
)
Prestamo = namedtuple(
    "Prestamo",
    [
        "folio",
        "isbn",
        "ejemplar",
        "cliente",
        "fechaprestamo",
        "fechadevolucion",
        "pagado",
        "notificado",
    ],
)


class GestorDatos(ABC):
    def __init__(self) -> None:
        self.conexion: pgdb.Connection = _conexion
        self.tabla = ""
        self.columnas = tuple()
        self.llave_primaria = tuple()
        self._clase_objeto_ = object

    def __llave_primaria_sql__(self):
        sql = tuple(f"{x[0]}={x[1]}" for x in self.llave_primaria)
        return " AND ".join(sql)

    def crear(self, objeto: NamedTuple):
        resultado = True
        try:
            tipos = tuple(tipo for columna, tipo in self.columnas)
            sentencia = f"INSERT INTO {self.tabla}"
            sentencia += f" VALUES ({', '.join(tipos)});"
            self.conexion.execute(sentencia, objeto)
            self.conexion.commit()
        except pgdb.Error as e:
            resultado = False
            print(f"Ha ocurrido un error. Detalles:\n{e}")
        return resultado

    def leer(self, llave_primaria: Iterable = None):
        resultado = None
        try:
            sentencia = f"SELECT * FROM {self.tabla}"
            if llave_primaria:
                sentencia += f" WHERE {self.__llave_primaria_sql__()};"
                resultado = self.conexion.execute(sentencia, llave_primaria)
            else:
                sentencia += ";"
                resultado = self.conexion.execute(sentencia)
            objetos = []
            for fila in resultado.fetchall():
                nueva_fila = []
                for atributo in fila:
                    if isinstance(atributo, str):
                        nueva_fila.append(atributo.strip())
                    else:
                        nueva_fila.append(atributo)
                objetos.append(self._clase_objeto_(*fila))
                objetos.sort()
            resultado = objetos

            if llave_primaria:
                if resultado:
                    resultado = resultado[0]
                else:
                    resultado = None
        except pgdb.Error as e:
            resultado = False
            print(f"Ha ocurrido un error. Detalles:\n{e}")
        return resultado

    def actualizar(self, llave_primaria: Iterable, objeto: NamedTuple):
        resultado = True
        try:
            columnas = tuple(f"{columna}={tipo}" for columna, tipo in self.columnas)
            columnas = ", ".join(columnas)
            parametros = list(objeto)
            parametros.extend(llave_primaria)
            sentencia = f"UPDATE {self.tabla}"
            sentencia += f" SET {columnas}"
            sentencia += f" WHERE {self.__llave_primaria_sql__()};"
            self.conexion.execute(sentencia, parametros)
            self.conexion.commit()
        except pgdb.Error as e:
            resultado = False
            print(f"Ha ocurrido un error. Detalles:\n{e}")
        return resultado

    def eliminar(self, llave_primaria: Iterable):
        resultado = True
        try:
            sentencia = f"DELETE FROM {self.tabla}"
            sentencia += f" WHERE {self.__llave_primaria_sql__()};"
            self.conexion.execute(sentencia, llave_primaria)
            self.conexion.commit()
        except pgdb.Error as e:
            resultado = False
            print(f"Ha ocurrido un error. Detalles:\n{e}")
        return resultado


class GestorAlumnos(GestorDatos):
    def __init__(self):
        super().__init__()
        self.tabla = "alumno"
        self.columnas = (
            Columna("codigo", "%d"),
            Columna("nombre", "%s"),
            Columna("carrera", "%s"),
            Columna("correo", "%s"),
        )
        self.llave_primaria = (Columna("codigo", "%d"),)
        self._clase_objeto_ = Alumno

    def crear(self, codigo: int, nombre: str, carrera: str, correo: str):
        alumno = Alumno(codigo, nombre, carrera, correo)
        return super().crear(alumno)

    def leer(self, codigo: int = None) -> list[Alumno] | Alumno | None | False:
        if codigo:
            llave_primaria = (codigo,)
            return super().leer(llave_primaria)
        else:
            return super().leer()

    def actualizar(self, codigo: int, nombre: str, carrera: str, correo: str):
        llave_primaria = (codigo,)
        alumno = Alumno(codigo, nombre, carrera, correo)
        return super().actualizar(llave_primaria, alumno)

    def eliminar(self, codigo: int):
        llave_primaria = (codigo,)
        return super().eliminar(llave_primaria)


class GestorProfesores(GestorDatos):
    def __init__(self):
        super().__init__()
        self.tabla = "profesor"
        self.columnas = (
            Columna("codigo", "%d"),
            Columna("nombre", "%s"),
            Columna("carrera", "%s"),
            Columna("correo", "%s"),
        )
        self.llave_primaria = (Columna("codigo", "%d"),)
        self._clase_objeto_ = Profesor

    def crear(self, codigo: int, nombre: str, carrera: str, correo: str):
        profesor = Profesor(codigo, nombre, carrera, correo)
        return super().crear(profesor)

    def leer(self, codigo: int = None) -> list[Profesor] | Profesor | None | False:
        if codigo:
            llave_primaria = (codigo,)
            return super().leer(llave_primaria)
        else:
            return super().leer()

    def actualizar(self, codigo: int, nombre: str, carrera: str, correo: str):
        llave_primaria = (codigo,)
        profesor = Profesor(codigo, nombre, carrera, correo)
        return super().actualizar(llave_primaria, profesor)

    def eliminar(self, codigo: int):
        llave_primaria = (codigo,)
        return super().eliminar(llave_primaria)


class GestorLibros(GestorDatos):
    def __init__(self):
        super().__init__()
        self.tabla = "libro"
        self.columnas = (
            Columna("isbn", "%s"),
            Columna("titulo", "%s"),
            Columna("autor", "%s"),
            Columna("editorial", "%s"),
            Columna("aniopublicacion", "%d"),
            Columna("ejemplar", "%d"),
            Columna("disponible", "%s"),
        )
        self.llave_primaria = (Columna("isbn", "%s"), Columna("ejemplar", "%d"))
        self._clase_objeto_ = Libro

    def crear(
        self,
        isbn: str,
        titulo: str,
        autor: str,
        editorial: str,
        aniopublicacion: int,
        ejemplar: int,
        disponible: bool = True,
    ):
        libro = Libro(
            isbn, titulo, autor, editorial, aniopublicacion, ejemplar, disponible
        )
        return super().crear(libro)

    def leer(
        self, isbn: str = None, ejemplar: int = None
    ) -> list[Libro] | Libro | None | False:
        if isbn and ejemplar:
            llave_primaria = (isbn, ejemplar)
            return super().leer(llave_primaria)
        else:
            return super().leer()

    def actualizar(
        self,
        isbn: str,
        ejemplar: int,
        titulo: str,
        autor: str,
        editorial: str,
        aniopublicacion: int,
        disponible: bool = True,
    ):
        llave_primaria = (isbn, ejemplar)
        libro = Libro(
            isbn, titulo, autor, editorial, aniopublicacion, ejemplar, disponible
        )
        return super().actualizar(llave_primaria, libro)

    def eliminar(self, isbn: str, ejemplar: int):
        llave_primaria = (isbn, ejemplar)
        return super().eliminar(llave_primaria)


class GestorPrestamos(GestorDatos):
    def __init__(self):
        super().__init__()
        self.tabla = "prestamo"
        self.columnas = (
            Columna("folio", "%d"),
            Columna("isbn", "%s"),
            Columna("ejemplar", "%d"),
            Columna("cliente", "%d"),
            Columna("fechaprestamo", "%s"),
            Columna("fechadevolucion", "%s"),
            Columna("pagado", "%s"),
            Columna("notificado", "%s"),
        )
        self.llave_primaria = (Columna("folio", "%d"),)
        self._clase_objeto_ = Prestamo

    def crear(
        self,
        folio: int,
        isbn: str,
        ejemplar: int,
        cliente: int,
        fechaprestamo: str,
    ):
        prestamo = Prestamo(
            folio,
            isbn,
            ejemplar,
            cliente,
            fechaprestamo,
            None,
            False,
            False,
        )
        return super().crear(prestamo)

    def leer(self, folio: int = None) -> list[Prestamo] | Prestamo | None | False:
        if folio:
            llave_primaria = (folio,)
            return super().leer(llave_primaria)
        else:
            return super().leer()

    def actualizar(
        self,
        folio: int,
        isbn: str,
        ejemplar: int,
        cliente: int,
        fechaprestamo: str,
        fechadevolucion: str = None,
        pagado: bool = False,
        notificado: bool = False,
    ):
        llave_primaria = (folio,)
        prestamo = Prestamo(
            folio,
            isbn,
            ejemplar,
            cliente,
            fechaprestamo,
            fechadevolucion,
            pagado,
            notificado,
        )
        return super().actualizar(llave_primaria, prestamo)

    def eliminar(self, folio: int):
        llave_primaria = (folio,)
        return super().eliminar(llave_primaria)


class VentanaInicioSesion(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Biblioteca Universidad Tecnológica")
        self.layout = QVBoxLayout()
        self.usuario = None

        self.usuario_edit = QLineEdit()
        self.contrasena_edit = QLineEdit()
        self.contrasena_edit.setEchoMode(QLineEdit.EchoMode.Password)

        self.boton_inicio = QPushButton("Iniciar sesión")
        self.boton_inicio.clicked.connect(self.__iniciar_sesion__)

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

    def __iniciar_sesion__(self):
        nombre = self.usuario_edit.text()
        contrasena = self.contrasena_edit.text()
        datos_usuarios = {}

        self.etiqueta_info.setText("Iniciando sesión...")
        self.etiqueta_info.setVisible(True)

        try:
            resultado_bd = _conexion.execute("SELECT * FROM usuario;").fetchall()
            if resultado_bd:
                for usuario in resultado_bd:
                    usuario = Usuario(
                        usuario.nombre.strip(), usuario.hash, usuario.nivel
                    )
                    datos_usuarios[usuario.nombre] = usuario

        except pgdb.Error as e:
            print("Error:", e)
            self.etiqueta_info.setText(
                "Error interno: Revisa la consola para más detalles."
            )

        if nombre in datos_usuarios:
            if self.__validar__(contrasena, datos_usuarios[nombre].hash):
                self.usuario = datos_usuarios[nombre]
                self.accept()
            else:
                self.etiqueta_info.setText("Contraseña incorrecta.")
        else:
            self.etiqueta_info.setText("Usuario no encontrado.")

    @staticmethod
    def __validar__(clave: str, hash_original: str):
        hash_clave = hashlib.sha512(clave.encode()).hexdigest()
        return hash_clave == hash_original


class VentanaPrincipal(QMainWindow):
    def __init__(self, nivel_usuario: int):
        super().__init__()
        self.setWindowTitle("Biblioteca Universidad Tecnológica")
        self.conexion_db = _conexion
        self.nivel_usuario = nivel_usuario

        self.gestor_alumnos = GestorAlumnos()
        self.gestor_profesores = GestorProfesores()
        self.gestor_libros = GestorLibros()
        self.gestor_prestamos = GestorPrestamos()

        self.layout = QGridLayout()
        self.widget_central = QLabel("")
        self.widget_central.setLayout(self.layout)
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

        self.__crear_menus__()

    def __crear_menus__(self):
        self.barra_menus = self.menuBar()

        # Archivo
        self.menu_archivo = self.barra_menus.addMenu("A&rchivo")
        self.archivo_salir = self.__crear_accion__(
            "&Salir",
            self,
            "Ctrl+Q",
            "Sale de la aplicación",
            self.close,
            self.menu_archivo,
        )

        # Alumnos
        if self.nivel_usuario == NIVEL_ADMINISTRADOR:
            self.menu_alumnos = self.barra_menus.addMenu("&Alumnos")
            self.alumno_todos = self.__crear_accion__(
                "&Ver alumnos",
                self,
                "Ctrl+A",
                "Muestra todos los alumnos en el sistema",
                self.ver_alumnos,
                self.menu_alumnos,
            )
            self.menu_alumnos.addSeparator()
            self.alumno_registrar = self.__crear_accion__(
                "&Nuevo alumno",
                self,
                None,
                "Registra un nuevo alumno",
                self.nuevo_alumno,
                self.menu_alumnos,
            )
            self.alumno_editar = self.__crear_accion__(
                "&Editar alumno",
                self,
                None,
                "Modifica la información de un alumno",
                self.editar_alumno,
                self.menu_alumnos,
            )
            self.alumno_borrar = self.__crear_accion__(
                "&Borrar alumno",
                self,
                None,
                "Elimina a un alumno del sistema",
                self.eliminar_alumno,
                self.menu_alumnos,
            )

        # Profesores
        if self.nivel_usuario == NIVEL_ADMINISTRADOR:
            self.menu_profesor = self.barra_menus.addMenu("Pro&fesores")
            self.profesor_todos = self.__crear_accion__(
                "&Ver profesores",
                self,
                "Ctrl+A",
                "Muestra todos los profesores en el sistema",
                self.ver_profesores,
                self.menu_profesor,
            )
            self.menu_profesor.addSeparator()
            self.profesor_registrar = self.__crear_accion__(
                "&Nuevo profesor",
                self,
                None,
                "Registra un nuevo profesor",
                self.nuevo_profesor,
                self.menu_profesor,
            )
            self.profesor_editar = self.__crear_accion__(
                "&Editar profesor",
                self,
                None,
                "Modifica la información de un profesor",
                self.editar_profesor,
                self.menu_profesor,
            )
            self.profesor_borrar = self.__crear_accion__(
                "&Borrar profesor",
                self,
                None,
                "Elimina a un profesor del sistema",
                self.eliminar_profesor,
                self.menu_profesor,
            )

        # Libros
        self.menu_libros = self.barra_menus.addMenu("&Libros")
        self.libro_todos = self.__crear_accion__(
            "&Ver libros",
            self,
            "Ctrl+L",
            "Muestra todos los libros en el sistema",
            self.ver_libros,
            self.menu_libros,
        )
        self.libro_todos = self.__crear_accion__(
            "&Buscar libros",
            self,
            "Ctrl+B",
            "Permite buscar libros en el sistema",
            self.buscar_libros,
            self.menu_libros,
        )
        if self.nivel_usuario == NIVEL_ADMINISTRADOR:
            self.menu_libros.addSeparator()
            self.libro_registrar = self.__crear_accion__(
                "&Nuevo libro",
                self,
                None,
                "Registra un nuevo libro",
                self.nuevo_libro,
                self.menu_libros,
            )
            self.libro_editar = self.__crear_accion__(
                "&Editar libro",
                self,
                None,
                "Modifica la información de un libro",
                self.editar_libro,
                self.menu_libros,
            )
            self.libro_borrar = self.__crear_accion__(
                "&Borrar libro",
                self,
                None,
                "Elimina un libro del sistema",
                self.eliminar_libro,
                self.menu_libros,
            )

        # Préstamos
        self.menu_prestamos = self.barra_menus.addMenu("&Préstamos")
        self.prestamo_todos = self.__crear_accion__(
            "&Ver préstamos",
            self,
            "Ctrl+P",
            "Muestra todos los préstamos en el sistema",
            self.ver_prestamos,
            self.menu_prestamos,
        )
        self.menu_prestamos.addSeparator()
        if self.nivel_usuario != NIVEL_ADMINISTRADOR:
            self.prestamo_registrar = self.__crear_accion__(
                "&Nuevo préstamo",
                self,
                None,
                "Registra un nuevo préstamo",
                self.nuevo_prestamo,
                self.menu_prestamos,
            )
            self.menu_prestamos.addSeparator()
            self.prestamo_devolver = self.__crear_accion__(
                "&Devolver préstamo",
                self,
                None,
                "Devuelve un préstamo",
                self.devolver_prestamo,
                self.menu_prestamos,
            )
            self.prestamo_devolver = self.__crear_accion__(
                "&Cobrar adeudo",
                self,
                None,
                "Genera los cobros pendientes de los adeudos de préstamos",
                self.cobrar_prestamo,
                self.menu_prestamos,
            )
            self.prestamo_devolver = self.__crear_accion__(
                "&Pagar adeudo",
                self,
                None,
                "Marca como pagados los cobros pendientes de los adeudos de préstamos",
                self.pagar_prestamo,
                self.menu_prestamos,
            )
        # if self.nivel_usuario == NIVEL_ADMINISTRADOR:
        #     self.prestamo_modificar = self.__crear_accion__(
        #         "&Modificar préstamo",
        #         self,
        #         None,
        #         "Modifica un préstamo",
        #         self.modificar_prestamo,
        #         self.menu_prestamos,
        #     )
        #     self.prestamo_borrar = self.__crear_accion__(
        #         "&Borrar préstamo",
        #         self,
        #         None,
        #         "Elimina un préstamo del sistema",
        #         self.eliminar_prestamo,
        #         self.menu_prestamos,
        #     )

    @staticmethod
    def __crear_accion__(
        texto: str,
        padre: QObject,
        atajo: str = None,
        tip: str = None,
        funcion=None,
        menu=None,
    ) -> QAction:
        accion = QAction(texto, padre)
        if atajo:
            accion.setShortcut(atajo)
        if tip:
            accion.setStatusTip(tip)
        if funcion:
            accion.triggered.connect(funcion)
        if menu:
            menu.addAction(accion)

        return accion

    def __msj__(self, entidad: str, linea1: str, linea2: str):
        QMessageBox.information(self, linea1 % entidad, linea2 % entidad)

    def ver_alumnos(self):
        VisorDatos(
            "Todos los alumnos",
            ("Codigo", "Nombre", "Carrera", "Correo"),
            self.gestor_alumnos,
        ).exec()

    def nuevo_alumno(self):
        campos = {
            "codigo": ("Código", None),
            "nombre": ("Nombre", None),
            "carrera": ("Carrera", None),
            "correo": ("Correo", None),
        }
        editor = EditorDatos("Nuevo alumno", campos)
        if editor.exec() == QDialog.DialogCode.Accepted:
            resultado = self.gestor_alumnos.crear(
                int(editor.controles["codigo"].text()),
                editor.controles["nombre"].text(),
                editor.controles["carrera"].text(),
                editor.controles["correo"].text(),
            )
            if resultado:
                self.__msj__("alumno", "Añadir %s", TEXTO_ADICION_CORRECTA)
            else:
                self.__msj__("alumno", "Añadir %s", TEXTO_ADICION_FALLIDA)

    def editar_alumno(self):
        alumno_id, ok_presionado = QInputDialog.getInt(
            self, "Modificar alumno", "ID del alumno a modificar:", 1, 1, 999999999, 1
        )
        alumno = self.gestor_alumnos.leer(alumno_id)
        if ok_presionado and alumno:
            campos = {
                "codigo": ("Código", alumno.codigo),
                "nombre": ("Nombre", alumno.nombre),
                "carrera": ("Carrera", alumno.carrera),
                "correo": ("Correo", alumno.correo),
            }
            editor = EditorDatos("Modificar alumno", campos)
            if editor.exec() == QDialog.DialogCode.Accepted:
                resultado = self.gestor_alumnos.crear(
                    int(editor.controles["codigo"].text()),
                    editor.controles["nombre"].text(),
                    editor.controles["carrera"].text(),
                    editor.controles["correo"].text(),
                )
                if resultado:
                    self.__msj__("alumno", "Modificar %s", TEXTO_EDICION_CORRECTA)
                else:
                    self.__msj__("alumno", "Modificar %s", TEXTO_EDICION_FALLIDA)

    def eliminar_alumno(self):
        codigo_alumno, ok_presionado = QInputDialog.getInt(
            self, "Eliminar alumno", "Código del alumno a eliminar:", 1, 1, 999999999, 1
        )
        if ok_presionado:
            respuesta = QMessageBox.question(
                self,
                "Eliminar alumno",
                "¿Estás seguro de que quieres eliminar al alumno?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta == QMessageBox.StandardButton.Yes:
                try:
                    self.gestor_alumnos.eliminar(codigo_alumno)
                    self.__msj__("alumno", "Eliminar %s", TEXTO_BORRADO_CORRECTO)
                except Exception:
                    self.__msj__("alumno", "Eliminar %s", TEXTO_BORRADO_FALLIDO)

    def ver_profesores(self):
        VisorDatos(
            "Todos los profesores",
            ("Codigo", "Nombre", "Carrera", "Correo"),
            self.gestor_profesores,
        ).exec()

    def nuevo_profesor(self):
        campos = {
            "codigo": ("Código", None),
            "nombre": ("Nombre", None),
            "carrera": ("Carrera", None),
            "correo": ("Correo", None),
        }
        editor = EditorDatos("Nuevo profesor", campos)
        if editor.exec() == QDialog.DialogCode.Accepted:
            resultado = self.gestor_profesores.crear(
                int(editor.controles["codigo"].text()),
                editor.controles["nombre"].text(),
                editor.controles["carrera"].text(),
                editor.controles["correo"].text(),
            )
            if resultado:
                self.__msj__("profesor", "Añadir %s", TEXTO_ADICION_CORRECTA)
            else:
                self.__msj__("profesor", "Añadir %s", TEXTO_ADICION_FALLIDA)

    def editar_profesor(self):
        codigo_profesor, ok_presionado = QInputDialog.getInt(
            self,
            "Modificar profesor",
            "ID del profesor a modificar:",
            1,
            1,
            999999999,
            1,
        )
        profesor = self.gestor_profesores.leer(codigo_profesor)
        if ok_presionado and profesor:
            campos = {
                "codigo": ("Código", profesor.codigo),
                "nombre": ("Nombre", profesor.nombre),
                "carrera": ("Carrera", profesor.carrera),
                "correo": ("Correo", profesor.correo),
            }
            editor = EditorDatos("Modificar profesor", campos)
            if editor.exec() == QDialog.DialogCode.Accepted:
                resultado = self.gestor_alumnos.actualizar(
                    int(editor.controles["codigo"].text()),
                    editor.controles["nombre"].text(),
                    editor.controles["carrera"].text(),
                    editor.controles["correo"].text(),
                )
                if resultado:
                    self.__msj__("profesor", "Modificar %s", TEXTO_EDICION_CORRECTA)
                else:
                    self.__msj__("profesor", "Modificar %s", TEXTO_EDICION_FALLIDA)

    def eliminar_profesor(self):
        codigo_profesor, ok_presionado = QInputDialog.getInt(
            self,
            "Eliminar profesor",
            "Código del profesor a eliminar:",
            1,
            1,
            999999999,
            1,
        )
        if ok_presionado:
            respuesta = QMessageBox.question(
                self,
                "Eliminar profesor",
                "¿Estás seguro de que quieres eliminar al profesor?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta == QMessageBox.StandardButton.Yes:
                try:
                    self.gestor_profesores.eliminar(codigo_profesor)
                    self.__msj__("profesor", "Eliminar %s", TEXTO_BORRADO_CORRECTO)
                except Exception:
                    self.__msj__("profesor", "Eliminar %s", TEXTO_BORRADO_FALLIDO)

    def ver_libros(self):
        VisorDatos(
            "Todos los libros",
            (
                "ISBN",
                "Titulo",
                "Autor",
                "Editorial",
                "Año de publicación",
                "Ejemplar",
                "Disponible",
            ),
            self.gestor_libros,
        ).exec()

    def buscar_libros(self):
        campos = {
            "isbn": ("ISBN", None),
            "titulo": ("Tïtulo", None),
            "autor": ("Autor", None),
            "editorial": ("Editorial", None),
            "aniopublicacion": ("Año de publicación", None),
        }
        columnas = list(columna[0] for columna in campos.values())
        columnas.extend(("Ejemplar", "Disponible"))
        editor = EditorDatos("Buscar libros por campo", campos, "Buscar")
        if editor.exec() == QMessageBox.DialogCode.Accepted:
            libros = self.gestor_libros.leer()
            libros_coincidentes = []
            for libro in libros:
                isbn = editor.controles["isbn"].text()
                titulo = editor.controles["titulo"].text()
                autor = editor.controles["autor"].text()
                editorial = editor.controles["editorial"].text()
                aniopublicacion = editor.controles["aniopublicacion"].text()

                if isbn and isbn.replace("-", "") in libro.isbn.replace("-", ""):
                    libros_coincidentes.append(libro)

                if titulo and titulo.lower() in libro.titulo.lower():
                    libros_coincidentes.append(libro)

                if autor and autor.lower() in libro.autor.lower():
                    libros_coincidentes.append(libro)

                if editorial and editorial.lower() in libro.editorial.lower():
                    libros_coincidentes.append(libro)

                if aniopublicacion and int(aniopublicacion) == libro.aniopublicacion:
                    libros_coincidentes.append(libro)

            VisorDatos(
                "Resultados de búsqueda", columnas, datos=libros_coincidentes
            ).exec()

    def nuevo_libro(self):
        campos = {
            "isbn": ("ISBN", None),
            "titulo": ("Tïtulo", None),
            "autor": ("Autor", None),
            "editorial": ("Editorial", None),
            "aniopublicacion": ("Año de publicación", None),
            "ejemplar": ("Ejemplar", None),
        }
        editor = EditorDatos("Nuevo libro", campos)
        if editor.exec() == QDialog.DialogCode.Accepted:
            resultado = self.gestor_libros.crear(
                editor.controles["isbn"].text(),
                editor.controles["titulo"].text(),
                editor.controles["autor"].text(),
                editor.controles["editorial"].text(),
                int(editor.controles["aniopublicacion"].text()),
                int(editor.controles["ejemplar"].text()),
            )
            if resultado:
                self.__msj__("libro", "Añadir %s", TEXTO_ADICION_CORRECTA)
            else:
                self.__msj__("libro", "Añadir %s", TEXTO_ADICION_FALLIDA)

    def editar_libro(self):
        isbn_libro, ok_presionado = QInputDialog.getText(
            self,
            "Modificar libro",
            "ISBN del libro a modificar:",
        )
        if not ok_presionado:
            return
        ejemplar_libro, ok_presionado = QInputDialog.getInt(
            self, "Modificar libro", "Ejemplar del libro a modificar:", 1, 1, 999, 1
        )
        if ok_presionado and isbn_libro and ejemplar_libro:
            libro = self.gestor_libros.leer(isbn_libro, ejemplar_libro)

        if libro:
            campos = {
                "isbn": ("ISBN", libro.isbn),
                "titulo": ("Tïtulo", libro.titulo),
                "autor": ("Autor", libro.autor),
                "editorial": ("Editorial", libro.editorial),
                "aniopublicacion": ("Año de publicación", libro.aniopublicacion),
                "ejemplar": ("Ejemplar", libro.ejemplar),
                "disponible": ("Disponible", libro.disponible),
            }
            editor = EditorDatos("Modificar libro", campos)
            if editor.exec() == QDialog.DialogCode.Accepted:
                resultado = self.gestor_libros.actualizar(
                    editor.controles["isbn"].text(),
                    editor.controles["titulo"].text(),
                    editor.controles["autor"].text(),
                    editor.controles["editorial"].text(),
                    int(editor.controles["aniopublicacion"].text()),
                    int(editor.controles["ejemplar"].text()),
                    bool(editor.controles["disponible"].text()),
                )
                if resultado:
                    self.__msj__("libro", "Modificar %s", TEXTO_EDICION_CORRECTA)
                else:
                    self.__msj__("libro", "Modificar %s", TEXTO_EDICION_FALLIDA)

    def eliminar_libro(self):
        # Obtener el ID del libro a eliminar mediante un cuadro de diálogo de entrada
        isbn_libro, ok_presionado = QInputDialog.getText(
            self, "Eliminar libro", "ISBN del Libro a eliminar:"
        )
        if not ok_presionado:
            return
        ejemplar_libro, ok_presionado = QInputDialog.getInt(
            self, "Eliminar libro", "Ejemplar del libro a eliminar:", 1, 1, 999, 1
        )
        if ok_presionado:
            # Mostrar un cuadro de confirmación antes de eliminar
            respuesta = QMessageBox.question(
                self,
                "Eliminar libro",
                "¿Estás seguro de que quieres eliminar este libro?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta == QMessageBox.StandardButton.Yes:
                try:
                    self.gestor_libros.eliminar(isbn_libro, ejemplar_libro)
                    self.__msj__("libro", "Eliminar %s", TEXTO_BORRADO_CORRECTO)
                except Exception:
                    self.__msj__("libro", "Eliminar %s", TEXTO_BORRADO_FALLIDO)

    def ver_prestamos(self):
        VisorDatos(
            "Todos los préstamos",
            (
                "Folio",
                "ISBN",
                "Ejemplar",
                "Código del cliente",
                "Fecha de préstamo",
                "Fecha de devolución",
                "Pagado",
                "Notificado",
            ),
            self.gestor_prestamos,
        ).exec()

    def nuevo_prestamo(self):
        campos = {
            "isbn": ("ISBN", None),
            "ejemplar": ("Ejemplar", None),
            "cliente": ("Código de usuario", None),
        }
        editor = EditorDatos("Nuevo préstamo", campos)
        if editor.exec() == QDialog.DialogCode.Accepted:
            try:
                folios = self.gestor_prestamos.leer()

                if folios:
                    folio = folios[-1].folio + 1
                else:
                    folio = 1

                codigo_cliente = int(editor.controles["cliente"].text())
                cliente = self.gestor_alumnos.leer(codigo_cliente)

                if not cliente:
                    cliente = self.gestor_profesores.leer(codigo_cliente)

                if not cliente:
                    raise IndexError("Código de cliente no encontrado")

                isbn = editor.controles["isbn"].text()
                ejemplar = int(editor.controles["ejemplar"].text())
                fechasolicitud = datetime.today()
                fechadevolucion = fechasolicitud + timedelta(NUM_DIAS_PRESTAMO)
                libro = self.gestor_libros.leer(isbn, ejemplar)

                if not libro.disponible:
                    raise ValueError("Libro no disponible")

                resultado = self.gestor_prestamos.crear(
                    folio,
                    isbn,
                    ejemplar,
                    codigo_cliente,
                    fechasolicitud.strftime(FORMATO_FECHA),
                )

                if not resultado:
                    raise ValueError("Ocurrió un error al realizar la adición.")

                self.gestor_libros.actualizar(
                    libro.isbn,
                    libro.ejemplar,
                    libro.titulo,
                    libro.autor,
                    libro.editorial,
                    libro.aniopublicacion,
                    False,
                )

                self.__enviar_correo__(
                    cliente.correo,
                    TEXTO_ASUNTO_SOLICITUD_PRESTAMO,
                    TEXTO_CONTENIDO_SOLICITUD_PRESTAMO.format(
                        cliente.nombre,
                        folio,
                        cliente.codigo,
                        libro.titulo,
                        libro.autor,
                        libro.aniopublicacion,
                        libro.isbn,
                        libro.ejemplar,
                        fechasolicitud,
                        fechadevolucion,
                    ),
                )
                self.__msj__("préstamo", "Añadir %s", TEXTO_ADICION_CORRECTA)

            except (IndexError, ValueError) as e:
                print(f"Ha ocurrido un error. Detalles:\n{e}")
                self.__msj__("préstamo", "Añadir %s", TEXTO_ADICION_FALLIDA)

    def modificar_prestamo(self):
        folio_prestamo, ok_presionado = QInputDialog.getInt(
            self,
            "Modificar préstamo",
            "Folio del préstamo a modificar:",
            1,
            1,
            999999999,
            1,
        )
        prestamo = self.gestor_prestamos.leer(folio_prestamo)
        if ok_presionado and prestamo:
            campos = {
                "folio": ("Folio", prestamo.folio),
                "isbn": ("ISBN", prestamo.isbn),
                "ejemplar": ("Ejemplar", prestamo.ejemplar),
                "cliente": ("Código de usuario", prestamo.cliente),
                "fechaprestamo": ("Fecha de préstamo", prestamo.fechaprestamo),
                "fechadevolucion": ("Fecha de devolución", prestamo.fechadevolucion),
            }
            editor = EditorDatos("Modificar préstamo", campos)
            if editor.exec() == QDialog.DialogCode.Accepted:
                resultado = self.gestor_prestamos.actualizar(
                    int(editor.controles["folio"].text()),
                    editor.controles["isbn"].text(),
                    int(editor.controles["ejemplar"].text()),
                    int(editor.controles["cliente"].text()),
                    editor.controles["fechaprestamo"].text(),
                    editor.controles["fechadevolucion"].text(),
                )
                if resultado:
                    self.__msj__("préstamo", "Modificar %s", TEXTO_EDICION_CORRECTA)
                else:
                    self.__msj__("préstamo", "Modificar %s", TEXTO_EDICION_FALLIDA)

    def devolver_prestamo(self):
        folio_prestamo, ok_presionado = QInputDialog.getInt(
            self,
            "Devolver préstamo",
            "Folio del préstamo a devolver:",
            1,
            1,
            999999999,
            1,
        )
        prestamo = self.gestor_prestamos.leer(folio_prestamo)
        if ok_presionado and prestamo:
            respuesta = QMessageBox.question(
                self,
                "Devolver préstamo",
                f"¿Estás seguro de que quieres marcar el préstamo {folio_prestamo:010} como devuelto?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta == QMessageBox.StandardButton.Yes:
                libro = self.gestor_libros.leer(prestamo.isbn, prestamo.ejemplar)
                fechasolicitud = prestamo.fechaprestamo
                fecha_devolucion_acordada = fechasolicitud + timedelta(
                    NUM_DIAS_PRESTAMO
                )
                fecha_devolucion_real = datetime.today().date()
                pagado = fecha_devolucion_real <= fecha_devolucion_acordada
                devolucion_completa = self.gestor_prestamos.actualizar(
                    prestamo.folio,
                    prestamo.isbn,
                    prestamo.ejemplar,
                    prestamo.cliente,
                    fechasolicitud.strftime(FORMATO_FECHA),
                    fecha_devolucion_real.strftime(FORMATO_FECHA),
                    pagado,
                    prestamo.notificado,
                )
                devolucion_completa = (
                    devolucion_completa
                    and self.gestor_libros.actualizar(
                        libro.isbn,
                        libro.ejemplar,
                        libro.titulo,
                        libro.autor,
                        libro.editorial,
                        libro.aniopublicacion,
                        True,
                    )
                )
                if devolucion_completa:
                    self.__msj__("préstamo", "Devolver %s", TEXTO_EDICION_CORRECTA)
                    if not pagado:
                        QMessageBox.information(
                            self,
                            "Adeudos pendientes",
                            "La devolución ha generado una comisión. Haz tu pago correspondiente.",
                        )
                else:
                    self.__msj__("préstamo", "Devolver  %s", TEXTO_EDICION_FALLIDA)
        elif ok_presionado and not prestamo:
            self.__msj__(
                "préstamo", "Devolver %s", "El %s ingresado no ha sido encontrado."
            )

    def pagar_prestamo(self):
        folio, ok_presionado = QInputDialog.getInt(
            self,
            "Pagar adeudos",
            "Folio del préstamo:",
            1,
            1,
            999999999,
            1,
        )
        prestamo = self.gestor_prestamos.leer(folio)

        if ok_presionado and prestamo:
            if prestamo.fechadevolucion is None:
                QMessageBox.information(
                    self,
                    "Pago no disponible",
                    "Realiza la devolución del libro antes de marcar el pago.",
                )
            else:
                actualizar_pago = QMessageBox.question(
                    self,
                    "Pagar adeudo",
                    f"¿Estás seguro de que quieres marcar el adeudo del préstamo {folio:010} como pagado?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if actualizar_pago == QMessageBox.StandardButton.Yes:
                    actualizar_pago = self.gestor_prestamos.actualizar(
                        folio,
                        prestamo.isbn,
                        prestamo.ejemplar,
                        prestamo.cliente,
                        prestamo.fechaprestamo,
                        prestamo.fechadevolucion,
                        True,
                        prestamo.notificado,
                    )
                    if actualizar_pago:
                        self.__msj__("adeudo", "Pagar %s", TEXTO_EDICION_CORRECTA)
                    else:
                        self.__msj__("adeudo", "Pagar %s", TEXTO_EDICION_FALLIDA)

    def cobrar_prestamo(self):
        codigo_cliente, ok_presionado = QInputDialog.getInt(
            self,
            "Cobrar adeudos",
            "Código del cliente:",
            1,
            1,
            999999999,
            1,
        )
        cliente = self.gestor_alumnos.leer(
            codigo_cliente
        ) or self.gestor_profesores.leer(codigo_cliente)
        if ok_presionado and cliente:
            cant_adeudos = 0
            prestamos = self.gestor_prestamos.leer()
            hoy = datetime.today().strftime(FORMATO_FECHA)
            nombre_archivo = pathlib.Path(f"./{codigo_cliente:09}-{hoy}.pdf").absolute()
            lienzo = canvas.Canvas(str(nombre_archivo), letter)
            lienzo_y = 750

            for prestamo in prestamos:
                if (
                    prestamo.pagado
                    or codigo_cliente != prestamo.cliente
                    or prestamo.fechadevolucion is None
                ):
                    continue
                fechaprestamo = prestamo.fechaprestamo
                fechadevolucion = prestamo.fechadevolucion
                dias_prestamo = (fechadevolucion - fechaprestamo).days
                dias_penalizacion = dias_prestamo - NUM_DIAS_PRESTAMO
                costo = dias_penalizacion * COSTO_DIA_PENALIZACION
                lienzo.drawString(
                    80,
                    lienzo_y,
                    f"Préstamo {prestamo.folio:010}: ${costo:4} ({dias_penalizacion} dias de penalización)",
                )
                lienzo_y -= 20
                cant_adeudos += 1

            if cant_adeudos == 0:
                lienzo.drawString(
                    80,
                    lienzo_y,
                    "Sin adeudos pendientes de pago",
                )

            lienzo.save()
            QDesktopServices.openUrl(QUrl(nombre_archivo.as_uri()))

    def eliminar_prestamo(self):
        # Obtener el ID del préstamo a eliminar mediante un cuadro de diálogo de entrada
        folio_prestamo, ok_presionado = QInputDialog.getInt(
            self, "Eliminar préstamo", "Folio del préstamo a eliminar:", 1, 1, 100000, 1
        )
        if ok_presionado:
            # Mostrar un cuadro de confirmación antes de eliminar
            respuesta = QMessageBox.question(
                self,
                "Eliminar préstamo",
                "¿Estás seguro de que quieres eliminar este préstamo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta == QMessageBox.StandardButton.Yes:
                try:
                    self.gestor_prestamos.eliminar(folio_prestamo)
                    self.__msj__("préstamo", "Eliminar %s", TEXTO_BORRADO_CORRECTO)
                except Exception:
                    self.__msj__("préstamo", "Eliminar %s", TEXTO_BORRADO_FALLIDO)

    def notificar_prestamo(self):
        for prestamo in self.gestor_prestamos.leer():
            fechasolicitud = datetime.strptime(prestamo.fechaprestamo, FORMATO_FECHA)
            fecha_devolucion_acordada = fechasolicitud + timedelta(NUM_DIAS_PRESTAMO)
            if (datetime.today() - fechasolicitud).days < 2:
                cliente = self.gestor_alumnos.leer(
                    prestamo.cliente
                ) or self.gestor_profesores.leer(prestamo.cliente)
                libro = self.gestor_libros.leer(prestamo.isbn, prestamo.ejemplar)
                self.__enviar_correo__(
                    cliente.correo,
                    TEXTO_ASUNTO_RECORDATORIO_PRESTAMO,
                    TEXTO_CONTENIDO_RECORDATORIO_PRESTAMO.format(
                        cliente.nombre,
                        prestamo.folio,
                        libro.titulo,
                        fecha_devolucion_acordada,
                    ),
                )

    def __enviar_correo__(self, destinatario: str, titulo: str, contenido: str):
        cliente = yagmail.SMTP(USUARIO_GMAIL, CLAVE_GMAIL)
        cliente.send(destinatario, titulo, contenido)


class VisorDatos(QDialog):
    def __init__(
        self,
        titulo: str,
        columnas: list[str],
        datos: GestorDatos | Iterable[Iterable[str]],
        padre: QWidget = None,
    ):
        super().__init__(padre)
        self.setWindowTitle(titulo)
        self.conexion_db = _conexion

        self.layout = QVBoxLayout()
        self.setWindowIcon(QIcon("icon.png"))
        redimensionar_y_centrar_widget(self, 640, 480)

        self.tabla = QTableWidget(self)
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla.setHorizontalHeaderLabels(columnas)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setFixedSize(600, 440)
        self.layout.addWidget(self.tabla)
        self.layout.setAlignment(self.tabla, Qt.AlignmentFlag.AlignCenter)
        self.layout.setSizeConstraint(self.layout.SizeConstraint.SetMaximumSize)
        self.setLayout(self.layout)
        self.__llenar_tabla__(datos)

    def __llenar_tabla__(self, datos: GestorDatos | Iterable[Iterable[str]]):
        self.tabla.setRowCount(0)
        if isinstance(datos, GestorDatos):
            filas = datos.leer()
        else:
            filas = datos

        if filas:
            self.tabla.setRowCount(len(filas))
            for i, fila in enumerate(filas):
                for j, atributo in enumerate(fila):
                    if isinstance(atributo, bool):
                        texto = "Si" if atributo else "No"
                    elif atributo is None:
                        texto = "Sin registro"
                    else:
                        texto = str(atributo)
                    self.tabla.setItem(i, j, QTableWidgetItem(texto))


class EditorDatos(QDialog):
    def __init__(
        self, titulo: str, datos: dict[str, Any], texto_boton: str = "Guardar"
    ):
        super().__init__()
        self.setWindowTitle(f"{titulo} - Biblioteca Universidad Tecnológica")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Dialog)
        self.layout = QVBoxLayout()

        # Cambia el tamaño de la ventana y la centra
        self.resize(350, 250)
        self.move(500, 250)

        self.conexion_db = _conexion
        self.controles = {}

        for id_control, datos_control in datos.items():
            etiqueta_control, valor_control = datos_control

            self.layout.addWidget(QLabel(etiqueta_control))
            self.controles[id_control] = QLineEdit()
            self.layout.addWidget(self.controles[id_control])

            if valor_control:
                self.controles[id_control].setText(str(valor_control))

        self.boton_guardar = QPushButton(texto_boton)
        self.layout.addWidget(self.boton_guardar)
        self.boton_guardar.clicked.connect(self.aceptar)

        self.etiqueta_info = QLabel("")
        self.etiqueta_info.setVisible(False)
        self.layout.addWidget(self.etiqueta_info)

        self.setLayout(self.layout)

    def aceptar(self):
        self.accept()
        self.close()


if __name__ == "__main__":
    main()
