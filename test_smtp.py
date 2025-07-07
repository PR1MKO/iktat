import smtplib

try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('kiss.istvan.professional@gmail.com', 'zjiy imdc sfvq yaph')
    print("Connected and logged in!")
    server.quit()
except Exception as e:
    print("Error:", e)
