from flask import Flask, render_template,flash,redirect,url_for,session,request
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from wtforms import Form,StringField,PasswordField, form,validators,SelectField,BooleanField,IntegerField,TextAreaField
from passlib.hash import sha256_crypt
from functools import wraps
import base64
#import os
import cv2
import numpy as np
import pytesseract as tess
tess.pytesseract.tesseract_cmd = r'C:\Users\acer\AppData\Local\Tesseract-OCR\tesseract.exe'

app = Flask(__name__)

#MySQL Database ayarları 
mysql = MySQL(app)
app.secret_key = "bombacımülayim"
app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"] = "dorukdb"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"


#Listeleri stringe çevirme fonksiyonu
def listToString(s): 
    
    str1 = "" 
     
    for ele in s: 
        str1 += " "+ele  
    
    return str1 


#Image Processing ve image'den text çıkarma
def imgtotext(x):
    
    h = x.decode("utf-8")
    
    imgpath = stringToRGB(h)
    
    kernel = np.ones((1, 1), np.uint8) # Erode ve Dilate için kernel
    #img = cv2.imread(imgpath)
    img = cv2.resize(imgpath, None, fx=1.2, fy=1.2, interpolation=cv2.INTER_CUBIC)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.erode(img, kernel, iterations=1)
    #img = cv2.adaptiveThreshold(cv2.bilateralFilter(img, 9, 75, 75), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
    
    result = tess.image_to_string(img,lang="tur")
    bill_data = result
    bill = bill_data.split()
    c = listToString(bill)
    return c

#base64 encoded image to RGB
def stringToRGB(base64_string):
    img_str = base64.b64decode(str(base64_string))
    image = np.frombuffer(img_str, np.uint8)
    img_np = cv2.imdecode(image, cv2.IMREAD_COLOR)
    return img_np

#Giriş yapılınca görüntülenebilecek sayfalar için
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu Sayfayı Görüntülemek için Lütfen Giriş Yapınız!")
            return redirect(url_for("login"))
    return decorated_function

#Giriş yapılınca görüntülenemeyecek sayfalar için
def not_logged(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            flash("Bu sayfayı görüntülemek için çıkış yapmalısınız!")
            return redirect(url_for("index"))
        else:
            return f(*args,**kwargs)
    return decorated_function

#Bazı sayfalar için yetkilendirme
def required_roles(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if get_current_user_role() not in roles:
                flash('Bu sayfayı görüntülemeye yetkiniz bulunmamaktadır.')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapped
    return wrapper

#Giriş yapan kullanıcının rolünü yakalama
def get_current_user_role():
    username = session["username"]
    cursor = mysql.connection.cursor()
    sorgu = "Select role From employees where username = %s"
    cursor.execute(sorgu,(username,))
    data = cursor.fetchone()
    role = str(data["role"])
    return role

app.jinja_env.globals.update(get_current_user_role=get_current_user_role) 
#Sessiondaki kullanıcının ismini yakalama
def get_current_user_name():
    username = session["username"]
    cursor = mysql.connection.cursor()
    sorgu = "Select name From employees where username = %s"
    cursor.execute(sorgu,(username,))
    data = cursor.fetchone()
    name = str(data["name"])
    return name

#Sessiondaki kullanıcının şirketini yakalama
def get_current_user_company():
    username = session["username"]
    cursor = mysql.connection.cursor()
    sorgu = "Select company From employees where username = %s"
    cursor.execute(sorgu,(username,))
    data = cursor.fetchone()
    company = str(data["company"])
    return company

#Fatura Yükleme Formu
class UploadForm(Form):
    description = StringField("Harcama Nedeni",validators=[
        validators.DataRequired("Bu alan boş bırakılamaz"),
        validators.length(min=5,max=50)
    ])
    accheck = BooleanField("Muhasebe Onayı",validators=[
        validators.DataRequired("Onaylamak için kutucuğu işaretleyiniz!"),
    ])
    managercheck = BooleanField("Yönetici Onayı",validators=[
        validators.DataRequired("Onaylamak için kutucuğu işaretleyiniz!"),
    ])
    billcontent = TextAreaField("Fatura İçeriği",validators=[
        validators.DataRequired("Bu alan boş bırakılamaz"),
    ])

#Giriş Formu
class LoginForm(Form):
    username = StringField("Kullanıcı Adı:")
    password = PasswordField("Şifre :")

#Admin Kayıt Formu
class GodRegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[
        validators.length(min=3,max=25),
        validators.DataRequired(message="Burası Boş Bırakılamaz")
    ])
    username = StringField("Kullanıcı Adı",validators=[
        validators.length(min=7,max=25),
        validators.DataRequired(message="Burası Boş Bırakılamaz")])
    email = StringField("Email Adresi",validators=[
        validators.length(min=10,max=50),
        validators.DataRequired(message="Burası Boş Bırakılamaz"),
        validators.Email(message="Lütfen Geçerli Bir Email Giriniz.")
    ])
    password = PasswordField("Parola:", validators=[
        validators.DataRequired(message="Lütfen Bir Parola Belirleyiniz"),
        validators.EqualTo(fieldname= "confirm",message="Parolanız Uyuşmuyor..."),
        validators.length(min=8,max=24)
    ])
    confirm = PasswordField("Parola Doğrula")
    role = SelectField("Rol",choices=["Çalışan","Muhasebe","İnsan Kaynakları","Yönetici","Admin"])
    company = StringField("Şirket",validators=[
        validators.length(min=3,max=40)
    ])
    phonenumber = IntegerField("Telefon Numarası",validators=[
        validators.DataRequired(message="Lütfen Telefon Numarası Giriniz"),
        validators.NumberRange(min=1000000000,max=9999999999,message="Lütfen 10 haneli Telefon Numarası Giriniz"),
    ])

#Yönetici İK Kayıt formu
class InterRegisterForm(Form):


    name = StringField("İsim Soyisim",validators=[
        validators.length(min=3,max=25),
        validators.DataRequired(message="Burası Boş Bırakılamaz")
    ])
    username = StringField("Kullanıcı Adı",validators=[
        validators.length(min=7,max=25),
        validators.DataRequired(message="Burası Boş Bırakılamaz")])
    email = StringField("Email Adresi",validators=[
        validators.length(min=10,max=50),
        validators.DataRequired(message="Burası Boş Bırakılamaz"),
        validators.Email(message="Lütfen Geçerli Bir Email Giriniz.")
    ])
    password = PasswordField("Parola:", validators=[
        validators.DataRequired(message="Lütfen Bir Parola Belirleyiniz"),
        validators.EqualTo(fieldname= "confirm",message="Parolanız Uyuşmuyor..."),
        validators.length(min=8,max=24)
    ])
    confirm = PasswordField("Parola Doğrula")
    role = SelectField("Departman",choices=["Çalışan","Muhasebe","İnsan Kaynakları"])
    phonenumber = IntegerField("Telefon Numarası",validators=[
        validators.DataRequired(message="Lütfen Telefon Numarası Giriniz"),
        validators.NumberRange(min=1000000000,max=9999999999,message="Lütfen 10 haneli Telefon Numarası Giriniz"),
    ])



@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login",methods=["GET","POST"])
@not_logged
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data
        cursor = mysql.connection.cursor()
        sorgu = "Select * From employees where username = %s"
        result = cursor.execute(sorgu,(username,))
        if result >0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                session["logged_in"] = True
                session["username"] = username
                flash("Hoşgeldin {}".format(username,))
                return redirect(url_for("index"))
            else:
                flash("Parolanız kullanıcı adı ile uyuşmuyor!")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor...")
            return redirect(url_for("login"))
    return render_template("login.html",form=form)

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Başarıyla çıkış yaptınız!")
    return redirect(url_for("index"))


@app.route("/godregister",methods=["GET","POST"])
@required_roles("Admin")
@login_required
def godregister():
    form = GodRegisterForm(request.form)
    if request.method == "POST" and form.validate():
        pic= request.files["pic"]
        image = base64.b64encode(pic.read())
        name = form.name.data
        username = form.username.data  
        email = form.email.data
        role = form.role.data
        phonenumber = str(form.phonenumber.data)
        password = sha256_crypt.encrypt(form.password.data)
        company = form.company.data
        cursor = mysql.connection.cursor()
        sorgu = "Insert into employees(name,username,email,password,role,company,phonenumber,image) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,username,email,password,role,company,phonenumber,image))
        mysql.connection.commit()
        cursor.close()
        flash("{} şirketine {} kişisi başarıyla eklendi!".format(company,name))
        return redirect(url_for("index"))
    else:
        return render_template("godregister.html",form=form)

@app.route("/adminregister",methods=["GET","POST"])
@required_roles("Yönetici","İnsan Kaynakları")
@login_required
def adminregister():
    form = InterRegisterForm(request.form)
    if request.method == "POST" and form.validate():
        cursor = mysql.connection.cursor()
        sorgu2= "Select username From employees where username=%s"
        result = cursor.execute(sorgu2,(form.username.data,))
        if result > 0 :
            flash("Bu kullanıcı adı kullanılmaktadır")
            return redirect(url_for("adminregister"))
        else:
            pic= request.files["pic"]
            image = base64.b64encode(pic.read())
            name = form.name.data
            username = form.username.data
            email = form.email.data
            role = form.role.data
            phonenumber = str(form.phonenumber.data)
            password = sha256_crypt.encrypt(form.password.data)
            company = get_current_user_company()
            sorgu = "Insert into employees(name,username,email,role,password,company,phonenumber,image) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"
            cursor.execute(sorgu,(name,username,email,role,password,company,phonenumber,image))
            mysql.connection.commit()
            cursor.close()
            flash("{} departmanına {} kişisi başarıyla eklendi!".format(role,name,))
            return redirect(url_for("index"))
        
    else:
        return render_template("adminregister.html",form=form)

@app.route("/employees",methods=["GET"])
@login_required
@required_roles("Yönetici","İnsan Kaynakları")
def employees():
    company=get_current_user_company()
    cursor = mysql.connection.cursor()
    sorgu = "Select * From employees where company =%s"
    result = cursor.execute(sorgu,(company,))
    if result >0:
        workers = cursor.fetchall()
        return render_template("employees.html",workers=workers)
    else:
        return render_template("employees.html")

@app.route("/employee/<string:id>",methods=["POST","GET"])
@login_required
@required_roles("Yönetici","İnsan Kaynakları")
def employee(id):
    company = get_current_user_company()
    cursor = mysql.connection.cursor()
    sorgu = "Select * From employees where id = %s"
    result = cursor.execute(sorgu,(id,))
    if result > 0:
        worker = cursor.fetchone()
        if company == worker["company"]:
            imagebyte = worker["image"]
            rimg = imagebyte.decode("utf-8")
            return render_template("employee.html",worker=worker,rimg=rimg)
        else:
            flash("Bu çalışanı görüntülemeye yetkiniz yok!")
            return redirect(url_for("employees"))
    else:
        flash("Böyle bir çalışan bulunamadı!")
        return redirect(url_for("employees"))

@app.route("/deleteemployee/<string:id>",methods=["POST","GET"])
@login_required
@required_roles("Yönetici","İnsan Kaynakları")
def deleteemployee(id):
    company = get_current_user_company()
    cursor = mysql.connection.cursor()
    sorgu = "Select * From employees where id=%s"
    result = cursor.execute(sorgu,(id,))
    if result>0:
        worker = cursor.fetchone()
        if company == worker["company"] and worker["role"] != "Yönetici":
            sorgu1= "Delete from employees where id=%s"
            cursor.execute(sorgu1,(id,))
            mysql.connection.commit()
            flash("{} çalışanı {} şirketinden silindi.".format(worker["name"],worker["company"]))
            return redirect(url_for("employees"))
        else:
            flash("Bu çalışan üzerinde işlem yapmaya yetkiniz yok!")
            return redirect(url_for("employees"))
    else:
        flash("Böyle bir çalışan yok!")
        return redirect(url_for("employees"))

@app.route("/profile",methods=["GET","POST"])
@login_required
def profile():
    username = session["username"]
    cursor = mysql.connection.cursor()
    sorgu = "Select * From employees where username = %s"
    result = cursor.execute(sorgu,(username,))
    if result>0:
        profil = cursor.fetchone()
        imagebyte = profil["image"]
        rimg = imagebyte.decode("utf-8")
        if request.method == "POST":
            if request.files["pic"]:
                pic= request.files["pic"]
                image = base64.b64encode(pic.read())
                sorgu1= "Update employees Set image = %s where username =%s"
                cursor.execute(sorgu1,(image,session["username"],))
                mysql.connection.commit()
                flash("Profil fotoğrafı güncellendi!")
                return redirect(url_for("profile"))
            else:
                flash("Fotoğraf Yüklenemediniz!")
                return redirect(url_for("profile"))
        else:
            return render_template("profile.html",profil=profil,rimg=rimg)
    else:
        return render_template("profile.html")


@app.route("/addbill",methods=["GET","POST"])
@login_required
def addbill():
    form = UploadForm(request.form)
    if request.method == "POST":
        if request.files["pic"]:
            pic= request.files["pic"]
            bill = base64.b64encode(pic.read())
            billcontent = imgtotext(bill)
            
            description = form.description.data
            company = get_current_user_company()
            filename = secure_filename(pic.filename)
            name = get_current_user_name()
            role = get_current_user_role()
            cursor = mysql.connection.cursor()
            sorgu = "Insert into bills(description,bill,company,filename,name,role,billcontent) VALUES(%s,%s,%s,%s,%s,%s,%s)"
            cursor.execute(sorgu,(description,bill,company,filename,name,role,billcontent))
            mysql.connection.commit()
            flash("Fatura başarıyla eklendi!")
            return redirect(url_for("index"))
        else:
            flash("Fatura resmini yüklemediniz!")
            return redirect(url_for("addbill"))
    else:
        return render_template("addbill.html",form=form)

@app.route("/bills")
@login_required
@required_roles("Yönetici","Muhasebe")
def bills():
    company = get_current_user_company()
    sorgu = "Select * From bills where company =%s"
    cursor = mysql.connection.cursor()
    result = cursor.execute(sorgu,(company,))
    if result>0:
        bills = cursor.fetchall()
        return render_template("bills.html",bills=bills)
    else:
        return render_template("bills.html")

@app.route("/bill/<string:id>",methods = ["GET","POST"])
@login_required
@required_roles("Yönetici","Muhasebe")
def bill(id):
    company = get_current_user_company()
    cursor = mysql.connection.cursor()
    sorgu = "Select * From bills where id =%s"
    result = cursor.execute(sorgu,(id,))
    if result >0:
        form = UploadForm(request.form)
        bill = cursor.fetchone()
        if bill["company"] == company:
            imdata = bill["bill"]
            img = imdata.decode("utf-8")
            if request.method == "POST":
                if get_current_user_role() == "Yönetici":
                    sorgu1 = "Update bills Set managercheck=%s where id =%s"
                    managercheck = form.managercheck.data
                    cursor.execute(sorgu1,(managercheck,id,))
                    mysql.connection.commit()
                    flash("Fatura Yönetim tarafından onaylandı!")
                    return redirect(url_for("bills"))
                else:
                    accheck = form.accheck.data
                    sorgu1 = "Update bills Set accheck=%s where id =%s"
                    cursor.execute(sorgu1,(accheck,id,))
                    mysql.connection.commit()
                    flash("Fatura Muhasebe tarafından onaylandı!")
                    return redirect(url_for("bills"))
            else:
                return render_template("bill.html",bill=bill,img=img,form=form)
        else:
            flash("Bu faturayı görüntülemeye yetkiniz yok!")
            return redirect(url_for("bills"))
    else:
        flash("Böyle bir fatura bulunamadı.")
        return redirect(url_for("bills"))



@app.route("/billsummary")
@login_required
@required_roles("Muhasebe","Yönetici")
def billsummary():
    company = get_current_user_company()
    cursor = mysql.connection.cursor()
    sorgu = "Select * From bills where accheck =%s and managercheck=%s and company=%s"
    result = cursor.execute(sorgu,(True,True,company,))
    if result>0:
        flar = cursor.fetchall()
        return render_template("billsummary.html",flar=flar)
    else:
        return render_template("billsummary.html")

@app.route("/deletebill/<string:id>",methods=["GET","POST"])
@login_required
@required_roles("Yönetici","Muhasebe")
def deletebill(id):
    company = get_current_user_company()
    cursor = mysql.connection.cursor()
    sorgu = "Select * From bills where id=%s"
    result = cursor.execute(sorgu,(id,))
    if result>0:
        bdata = cursor.fetchone()
        if bdata["company"] == company:
            sorgu1="Delete From bills where id=%s"
            cursor.execute(sorgu1,(id,))
            mysql.connection.commit()
            flash("Fatura başarıyla silindi!")
            return redirect(url_for("bills"))
        else:
            flash("Bu işlemi yapmaya yetkiniz bulunmamaktadır!")
            return redirect(url_for("bills"))
    else:
        flash("Böyle bir fatura bulunamadı!")
        return redirect(url_for("bills"))

@app.route("/billsum/<string:id>",methods=["GET","POST"])
@login_required
@required_roles("Yönetici","Muhasebe")
def billsum(id):
    company = get_current_user_company()
    sorgu = "Select * From bills where id =%s and company =%s"
    cursor = mysql.connection.cursor()
    result = cursor.execute(sorgu,(id,company,))
    if result>0:
        dbill = cursor.fetchone()
        if dbill["accheck"] and dbill["managercheck"]:
            if request.method == "POST":
                sorgu2 = "Delete From bills where id=%s"
                fatura = open("fatura.txt","w")
                fatura.write("{}\n\n**********************************************************\nFaturayı Yükleyen Kişi : {}\nFaturayı Yükleyen Departman : {}\nHarcama Nedeni : {}\n**********************************************************\nFatura İçeriği : {}\n\nBizi tercih ettiğiniz için Teşekkürler!".format(dbill["company"],dbill["name"],dbill["role"],dbill["description"],dbill["billcontent"]))
                fatura.close()
                sorgu2 = "Delete From bills where id=%s"
                cursor.execute(sorgu2,(id,))
                mysql.connection.commit()
                flash("Fatura, fatura.txt dosyasına kaydedildi!")
                return redirect(url_for("billsummary"))
            else:
                return render_template("billsum.html",dbill=dbill)
            
        else:
            flash("Bu fatura daha onay sürecinden geçmedi!")
            return redirect(url_for("bills"))
    else:
        flash("Böyle bir fatura yok!")
        return redirect(url_for("bills"))


if __name__ == '__main__':
    app.run(debug=True)
