from formation import AppBuilder

app = AppBuilder(path="calculator.xml")


def calculate(event=None):
    # event parameter needs to be there because using the bind method passes an event object
    # access the expr_var we created earlier to determine the current expression entered
    expr = app.expr_var.get()

    # evaluate the expression
    try:
        result = eval(expr)
    except Exception:
        # if the expression entered was malformed and could not be evaluated
        # we will display an error message instead
        result = "Invalid expression"

    # display the result
    app.result.config(text=result)


app.connect_callbacks(globals())

app.mainloop()