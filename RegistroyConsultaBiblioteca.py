import tkinter as tk
from tkinter import messagebox, ttk
import psycopg2

class Window:
    def __init__(self, ventana):
        self.ventana = ventana
        self.ventana.title("Registro de Alumnos")
        self.conn = None
        self.cur = None

        self.crear_ventana_login()

    def crear_ventana_login(self):
        self.ventana_login = tk.Toplevel(self.ventana)
        self.ventana_login.title("Inicio de Sesión")

        tk.Label(self.ventana_login, text="Usuario:").grid(row=0, column=0)
        self.user_entry = tk.Entry(self.ventana_login)
        self.user_entry.grid(row=0, column=1)

        tk.Label(self.ventana_login, text="Password:").grid(row=1, column=0)
        self.password_entry = tk.Entry(self.ventana_login, show="*")
        self.password_entry.grid(row=1, column=1)

        self.iniciar_sesion_button = tk.Button(self.ventana_login, text="Ingresar", command=self.iniciar_sesion)
        self.iniciar_sesion_button.grid(row=2, column=0, columnspan=2)

    def iniciar_sesion(self):
        user = self.user_entry.get()
        password = self.password_entry.get()

        if user == "isaacbarajaselizalde" and password == "12345":
            try:
                self.conn = psycopg2.connect(
                    dbname="Biblioteca",
                    user="isaacbarajaselizalde",
                    password="12345",
                    host="localhost"
                )
                print("Conexión exitosa!")
                self.cur = self.conn.cursor()

                self.ventana_login.destroy()
                self.mostrar_ventana_principal()
            except psycopg2.Error as e:
                print("Error al conectar:", e)
                messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.")

    def mostrar_ventana_principal(self):
        self.frame = tk.Frame(self.ventana)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Crear menú desplegable para seleccionar entre registro y consulta
        self.menu = tk.Menu(self.ventana)
        self.ventana.config(menu=self.menu)
        self.opciones_menu = tk.Menu(self.menu, tearoff=False)
        self.opciones_menu.add_command(label="Registro de Alumno", command=self.mostrar_registro_alumno)
        self.opciones_menu.add_command(label="Consulta Personalizada", command=self.mostrar_consulta_personalizada)
        self.menu.add_cascade(label="Opciones", menu=self.opciones_menu)

        # Crear tabla para mostrar los registros de alumnos
        self.tree = ttk.Treeview(self.frame, columns=("Código", "Nombre", "Carrera", "Correo"))
        self.tree.heading("#0")
        self.tree.heading("#1")
        self.tree.heading("#2")
        self.tree.heading("#3")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Botón para cargar registros de alumnos
        self.cargar_datos_button = tk.Button(self.frame, text="Cargar Registros", command=self.cargar_datos)
        self.cargar_datos_button.pack()

        # Campos para registrar nuevos alumnos
        self.codigo_entry = tk.Entry(self.ventana, width=30)
        tk.Label(self.ventana, text="Código:").pack()
        self.codigo_entry.pack()
        self.nombre_entry = tk.Entry(self.ventana, width=30)
        tk.Label(self.ventana, text="Nombre:").pack()
        self.nombre_entry.pack()
        self.carrera_entry = tk.Entry(self.ventana, width=30)
        tk.Label(self.ventana, text="Carrera:").pack()
        self.carrera_entry.pack()
        self.correo_entry = tk.Entry(self.ventana, width=30)
        tk.Label(self.ventana, text="Correo:").pack()
        self.correo_entry.pack()

        # Botón para guardar nuevo alumno
        self.guardar_button = tk.Button(self.ventana, text="Guardar Alumno", command=self.guardar_alumno)
        self.guardar_button.pack()

        # Campo de entrada para consulta personalizada
        self.consulta_entry = tk.Entry(self.ventana, width=30)
        tk.Label(self.ventana, text="Consulta SQL:").pack()
        self.consulta_entry.pack()

        # Botón para ejecutar consulta personalizada
        self.ejecutar_consulta_button = tk.Button(self.ventana, text="Ejecutar Consulta", command=self.ejecutar_consulta)
        self.ejecutar_consulta_button.pack()

    def mostrar_registro_alumno(self):
        self.limpiar_ventana()
        self.codigo_entry.pack()
        self.nombre_entry.pack()
        self.carrera_entry.pack()
        self.correo_entry.pack()
        self.guardar_button.pack()

    def mostrar_consulta_personalizada(self):
        self.limpiar_ventana()
        self.consulta_entry.pack()
        self.ejecutar_consulta_button.pack()

    def limpiar_ventana(self):
        self.codigo_entry.pack_forget()
        self.nombre_entry.pack_forget()
        self.carrera_entry.pack_forget()
        self.correo_entry.pack_forget()

    def cargar_datos(self):
        if self.cur is None:
            messagebox.showerror("Error", "No se ha establecido una conexión a la base de datos.")
            return

        # Limpiar tabla antes de cargar los registros
        for row in self.tree.get_children():
            self.tree.delete(row)

        try:
            self.cur.execute("SELECT codigo, nombre, carrera, correo FROM alumno;")
            rows = self.cur.fetchall()

            for row in rows:
                # Insertar cada fila con los valores en el orden correcto
                self.tree.insert("", "end", values=(row[0], row[1], row[2], row[3]))
        except psycopg2.Error as e:
            print("Error al ejecutar la consulta:", e)
            messagebox.showerror("Error", "Error al ejecutar consulta SQL.")

    def guardar_alumno(self):
        if self.cur is None:
            messagebox.showerror("Error", "No se ha establecido una conexión a la base de datos.")
            return

        codigo = self.codigo_entry.get()
        nombre = self.nombre_entry.get()
        carrera = self.carrera_entry.get()
        correo = self.correo_entry.get()

        consulta = "INSERT INTO alumno (codigo, nombre, carrera, correo) VALUES (%s, %s, %s, %s)"
        datos = (codigo, nombre, carrera, correo)
        try:
            self.cur.execute(consulta, datos)
            self.conn.commit()
            print("Datos insertados correctamente.")
            messagebox.showinfo("Registro Exitoso", "El alumno ha sido registrado correctamente.")
            self.cargar_datos()
        except psycopg2.Error as e:
            print("Error al insertar datos:", e)
            messagebox.showerror("Error", "Error al insertar datos en la base de datos.")

    def ejecutar_consulta(self):
        if self.cur is None:
            messagebox.showerror("Error", "No se ha establecido una conexión a la base de datos.")
            return

        consulta = self.consulta_entry.get()
        if not consulta:
            messagebox.showwarning("Advertencia", "Ingrese una consulta SQL válida.")
            return

        try:
            self.cur.execute(consulta)
            rows = self.cur.fetchall()

            for row in self.tree.get_children():
                self.tree.delete(row)

            for row in rows:
                self.tree.insert("", "end", values=row)
        except psycopg2.Error as e:
            print("Error al ejecutar la consulta:", e)
            messagebox.showerror("Error", "Error al ejecutar consulta SQL.")

ventana_principal = tk.Tk()
app = Window(ventana_principal)
ventana_principal.mainloop()
