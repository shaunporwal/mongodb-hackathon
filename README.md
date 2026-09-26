# MongoDB Hackathon

A starter repository for building a MongoDB-powered application during a hackathon. This project is intentionally lightweight so your team can move quickly from idea to prototype.

## Overview

This template gives you a clean starting point for:

- building a backend API with MongoDB
- storing and querying application data
- wiring in environment-based configuration
- creating a simple, reusable project foundation for demos and prototypes

## Tech Stack

The stack can be adapted to your hackathon goals, but a typical setup is:

- MongoDB
- Node.js
- Express or another lightweight backend framework
- JavaScript or TypeScript

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/shaunporwal/mongodb-hackathon.git
   cd mongodb-hackathon
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Configure your environment variables by creating a `.env` file:
   ```env
   PORT=3000
   MONGODB_URI=mongodb://localhost:27017/your-database-name
   ```
4. Start the development server:
   ```bash
   npm run dev
   ```

## Project Structure

```text
mongodb-hackathon/
├── README.md
├── package.json
├── .env.example
├── src/
│   ├── app.js
│   ├── config/
│   ├── routes/
│   ├── models/
│   └── services/
└── tests/
```

## Environment Variables

| Name | Description |
| --- | --- |
| `PORT` | Port for the server |
| `MONGODB_URI` | MongoDB connection string |

## Suggested Workflow

- define your data model
- connect to MongoDB
- build the endpoints your app needs
- validate flows with small sample data
- demo the MVP with a polished narrative

## Contributing

Use feature branches for work and keep commits small and descriptive.

```bash
git checkout -b feature/my-change
git add .
git commit -m "Add my change"
git push origin feature/my-change
```

## License

This project is provided as a hackathon starter and can be adapted for your own use.
