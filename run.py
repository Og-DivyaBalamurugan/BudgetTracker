from app import create_app

# Create the Flask application using our create_app function
app = create_app()

# This says "only run the server if this file is run directly"
# Not when it is imported by another file
if __name__ == '__main__':
    #app.run(debug=True)
    app.run(debug=True, port=8000)
    