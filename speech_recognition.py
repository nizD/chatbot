import speech_recognition as sr

r=sr.Recognizer()

with sr.Microphone() as source:
    print("Speak Anything")
    audio=r.listen(source)
    
    try:
        text=r.recognize_google(audio)
        print("You said: {}".format(text))
    except:
        text='sorry'
        print(text)
        
from gtts import gTTS
speech = gTTS(text)
speech.save('hello.mp3')
'''import pyttsx3
engine =pyttsx3.init()
engine.say(text)
engine.runAndWait()''' 