# Stage 1: Build the React app
FROM node:16-alpine as build
WORKDIR /app
# Copy package files and install dependencies
COPY package*.json ./
RUN npm install
# Copy the rest of the source code and build the app
COPY . .
RUN npm run build

# Stage 2: Serve the React app with Nginx
FROM nginx:stable-alpine
# Remove the default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy the build output from the previous stage to Nginx's directory
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
