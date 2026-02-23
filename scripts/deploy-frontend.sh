#!/bin/bash
set -e

# CV-Tailor Frontend Deployment Script
# Builds and deploys React frontend to S3 + CloudFront

# Load shared configuration
SCRIPT_DIR="$(dirname "$0")"
source "${SCRIPT_DIR}/config.sh"

echo "============================================"
echo "CV-Tailor Frontend Deployment"
echo "============================================"
echo ""

echo "Configuration:"
echo "  Region: ${AWS_REGION}"
echo "  S3 Bucket: ${S3_BUCKET}"
echo "  CloudFront ID: ${CLOUDFRONT_ID}"
echo "  API URL: ${API_URL}"
echo ""

# Step 1: Install dependencies
echo "Step 1/5: Installing dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
  npm install
  echo "✅ Dependencies installed"
else
  echo "✅ Dependencies already installed (skipping)"
fi
echo ""

# Step 2: Build production bundle
echo "Step 2/5: Building production bundle..."
echo "  Setting VITE_API_BASE_URL=${API_URL}"

# Create .env.production file
cat > .env.production <<EOF
VITE_API_BASE_URL=${API_URL}
EOF

npm run build
echo "✅ Build complete"
echo ""

# Step 3: Verify build output
echo "Step 3/5: Verifying build output..."
if [ ! -d "dist" ]; then
  echo "❌ Error: dist/ directory not found"
  exit 1
fi

FILE_COUNT=$(find dist -type f | wc -l)
echo "  Files built: ${FILE_COUNT}"
echo "✅ Build verified"
echo ""

# Step 4: Sync to S3
echo "Step 4/5: Uploading to S3..."
aws s3 sync dist/ s3://${S3_BUCKET}/ \
  --region ${AWS_REGION} \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "*.html" \
  --exclude "*.json"

# Upload HTML/JSON with shorter cache
aws s3 sync dist/ s3://${S3_BUCKET}/ \
  --region ${AWS_REGION} \
  --cache-control "no-cache" \
  --exclude "*" \
  --include "*.html" \
  --include "*.json"

echo "✅ Files uploaded to S3"
echo ""

# Step 5: Invalidate CloudFront cache
echo "Step 5/5: Invalidating CloudFront cache..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id ${CLOUDFRONT_ID} \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

echo "  Invalidation ID: ${INVALIDATION_ID}"
echo "  Waiting for invalidation to complete..."

aws cloudfront wait invalidation-completed \
  --distribution-id ${CLOUDFRONT_ID} \
  --id ${INVALIDATION_ID}

echo "✅ CloudFront cache invalidated"
echo ""

cd ..

echo "============================================"
echo "Deployment Complete!"
echo "============================================"
echo ""
echo "Frontend URL: ${FRONTEND_URL}"
echo "API URL: ${API_URL}"
echo ""
echo "Next Steps:"
echo "1. Open browser: ${FRONTEND_URL}"
echo "2. Test user registration/login"
echo "3. Verify API connectivity"
echo ""
echo "🎉 Frontend deployment complete!"
echo ""
