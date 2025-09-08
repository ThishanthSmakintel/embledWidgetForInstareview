require('dotenv').config();
const express = require('express');
const { dummyReviews } = require('./data');
const app = express();

app.use(express.static('.'));

// Serve widget with CORS headers
app.get('/widget.js', (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', process.env.CORS_ORIGIN || '*');
  res.setHeader('Content-Type', 'application/javascript');
  res.sendFile(__dirname + '/widget.js');
});
// API endpoint for widget
app.get('/api/reviews/:businessId', (req, res) => {
  res.json({ reviews: dummyReviews });
});

app.get('/admin', (req, res) => {
  res.sendFile(__dirname + '/admin.html');
});
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));