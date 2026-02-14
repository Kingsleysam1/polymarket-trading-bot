# Polymarket Multi-Strategy Trading Bot - Quick Deploy

This README provides quick instructions for deploying to Koyeb.

## 🚀 Quick Deployment

### Prerequisites
- Koyeb account (free tier available): https://koyeb.com
- GitHub account
-  Polygon wallet private key

### Deploy in 3 Steps

#### 1. Push to GitHub

```bash
# Run the deployment helper script
./deploy.sh

# Or manually:
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/polymarket-bot.git
git push -u origin main
```

#### 2. Deploy on Koyeb

1. Go to https://app.koyeb.com
2. Click "Create App"
3. Select "GitHub" and authorize
4. Choose your repository
5. **Set Builder**: Docker
6. **Add Environment Variables**:
   ```
   POLYGON_PRIVATE_KEY = your_key_here (mark as SECRET!)
   DRY_RUN = true
   PAPER_TRADING_ENABLED = true
   ```
7. Click "Deploy"

#### 3. Access Your Bot

Your bot will be live at: `https://your-app-name.koyeb.app`

Open that URL to see the trading dashboard!

---

## 📊 What's Included

- **Maker Market Making** - Captures spread with 0% fees
- **Probability Scalping** - Finds YES+NO arbitrage opportunities
- **Latency Arbitrage** - Exploits Binance→Polymarket lag (optional)
- **ML Pattern Recognition** - AI-powered trading (requires trained model)

---

## ⚙️ Configuration

All settings in `config.py`:
- Enable/disable strategies
- Adjust capital allocation
- Set risk limits
- Configure  thresholds

---

## 📖 Full Documentation

- **Deployment Guide**: `.gemini/antigravity/brain/.../koyeb_deployment_guide.md`
- **Implementation Walkthrough**: `.gemini/antigravity/brain/.../walkthrough.md`
- **README**: `README_MULTI_STRATEGY.md`

---

## 🔐 Security

**Never commit your `.env` file!**

The `.gitignore` is configured to exclude:
- `.env` and `.env.local`
- Private keys
- Log files
- Model data

Always set `POLYGON_PRIVATE_KEY` as a SECRET in Koyeb dashboard.

---

## 💰 Costs

- **Koyeb**: $0-5.50/month (free tier includes $5.50 credits)
- **Recommended**: Small instance ($5.50/month) for production
- **Trading Fees**: 0% maker, 2% taker on Polymarket

---

## 📞 Support

- Check logs in Koyeb dashboard
- See `koyeb_deployment_guide.md` for troubleshooting
- Monitor the dashboard for performance

---

**Deploy now and trade 24/7! 🚀**
