##############################################################################################
## Example written by PaulEcomaker: https://github.com/PaulEcomaker                         ##
## Example made using Formation Studio by Emmanuel Obara: https://github.com/ObaraEmmanuel  ##
##############################################################################################


from formation import AppBuilder
import threading

def comm_start():
    app.stop_event.clear()   ## clear the stop_event, just in case it is_set
    app.move_thread = threading.Thread(target=dotsfall)  ### create the thread for the movement of the dots
    app.move_thread.start()  ## start the thread of the movement.

    return

def dotsfall():
    listofdots2=[]  ### make a temporary second list of dots
    while not app.stop_event.is_set():  ## continue movement until stop_event
        for j in app.listofdots:  ### go over the list of dots
            if app.stop_event.is_set():
                break
            ID=j[0]  ## per dot read the ID
            speed=j[1]  ### per dot, read the speed
            app.Canvas1.move(ID,0,speed)  ### move the dot speed in Y+ direction
            speed+=1  ### increase the speed with 1
            if app.Canvas1.coords(ID)[1]<800: ### if the current y-coordinate of the dot is definitely higher than the bottom of the Canvas
                listofdots2.append([ID,speed])  ## add the ID and the new speed to the 2nd list-of-dots
        app.listofdots=listofdots2  ### after the for-loop: copy the 2nd list into the first
        if len(app.listofdots)>100:   ## this determines the update speed of the canvas after 1 for-loop
            waittime=int(max(10,100-(len(app.listofdots)/2)))  ### in case there are a lot of dots, update time is somewhere between 10 and 50
            app._root.after(waittime)  ## wait shorter if there are lost of dots
        else:
            app._root.after(50)  ### wait 50 ms so that movement is time limited
    # Ensure final update of canvas if needed
    app._root.update()
    return


def comm_stop():
    app.stop_event.set()   ## just raise the stop_event flag when the button is pressed
    return

def paint(event):
    python_green = "#476042"
    x1, y1 = (event.x - 1), (event.y - 1)   ## determine x-y coordinates (-1) is the left mouse-button is pressed
    x2, y2 = (event.x + 1), (event.y + 1)   ### the same, but (+1)
    ID=app.Canvas1.create_oval(x1, y1, x2, y2, fill=python_green) ## draw a dot (oval)
    app.listofdots.append([ID,1])  ## location of the dots (x1,y1,x2,y2) and initial speed when simulation starts
    return

def eraser():
    pass
    return


### build the app
app = AppBuilder(path="Canvas_example.json")
app.connect_callbacks(globals()) 

## determine some "global"-variables.
app.listofdots=[]  ### an empty list for the dots
app.stop_event = threading.Event()  ## a stop-Event

## run the app
app.mainloop()
