import http.client
import json
import DBMS
SMS_API_KEY = 'OWU2ODRjMWQtYmY5Ni00MGMwLTg2ODEtMmE0ZjcyNTE3ZDBhYjljNDVjNGU3NjA2Y2EwNDFhM2MzMzYzZWJiNDNhMjI='
def sending(recipients, message):
    conn = http.client.HTTPSConnection("api2.ippanel.com")
    payload = json.dumps({
        "recipient": recipients,
        "sending_type": "webservice",
        "sender": "+989982009417",
        "message": [
            message,
        ]
    })
    headers = {
        'accept': 'application/json',
        'apikey': SMS_API_KEY,
        'Content-Type': 'application/json'
    }
    conn.request("POST", "/api/v1/sms/send/webservice/peer-to-peer", payload, headers)
    res = conn.getresponse()
    data = res.read()
    # print(data.decode("utf-8"))


def sendClientsMessage(buyer = "محمد", buyer_phone = "09212242785", date = "jome" , time = "saat 6"):
    message =f"جناب آقا / سرکار خانم {buyer} ضمن عرض خوش امد گویی از شما برای برگزاری جلسه برسی یا انعقاد قرار داد شما دعوت به عمل می اوریم تا در تاریخ  {date} در ساعت  {time} به دفتر کارگزاری املاک ونوس واقع در خیابان معلم روبه روی شیرینی سرای مجلسی حضور به عمل اورید"
    sending([[buyer_phone]], message)


def sendOthersMessage(cons=7, date="jome", time="saat 6"):
    others = DBMS.get_other()
    recipients = []
    for other in others:
        recipients.append(other[4])
    recipients.append(DBMS.get_consultant_phone(cons))
    message =f"جلسه ای در تاریخ {date} ساعت {time} ثبت گردید حضور شما در این جلسه الزامیست لطفا در دفتر در زمان مشخص شده حضور به عمل آورید"
    sending([recipients], message)

def sendMessages(buyer, buyer_phone, customer, customer_phone, date, time, consultant):
    sendClientsMessage(buyer, buyer_phone, date, time)
    sendClientsMessage(customer, customer_phone, date, time)
    sendOthersMessage(consultant, date, time)
