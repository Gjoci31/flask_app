from app import create_app

app = create_app()

if __name__ == "__main__":
    # Run the application on port 5001 instead of the default 5000.
    # This avoids conflicts if port 5000 is already in use.
    app.run(debug=True, port=5001)

