"""
Send eamil based on outlook

"""
import os
import win32ui
import win32com.client as win32 

class EmailHandler(object):
    def __init__(self):
        pass

    def sendemail(self, strTo, strSubJect, strMsgText, strImagePath=None, strCc=None):
        # Check if Outlook is not open, and if so, open it before sending emails 
        def outlook_is_running():
            try:
                win32ui.FindWindow(None, "Microsoft Outlook")
                return True
            except win32ui.error:
                return False
            
        if not outlook_is_running():
            os.startfile("outlook")
                  
        outlook = win32.Dispatch('outlook.application') 
        mail = outlook.CreateItem(0) 
        mail.To = strTo
        mail.Cc = strCc 
        mail.Subject = strSubJect
        mail.Body = strMsgText 
        mail.Attachments.Add(strImagePath)
        mail.Send()
