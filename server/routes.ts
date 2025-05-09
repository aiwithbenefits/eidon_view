import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { SearchFilters, searchFiltersSchema } from "@shared/schema";
import { ZodError } from "zod";

export async function registerRoutes(app: Express): Promise<Server> {
  // API endpoints for Eidon functionality
  
  // Get timeline entries
  app.get('/api/timeline', async (req, res) => {
    const date = req.query.date as string;
    const page = parseInt(req.query.page as string || '1');
    const limit = parseInt(req.query.limit as string || '12');
    
    try {
      const result = await storage.getTimelineEntries(date, page, limit);
      res.json(result);
    } catch (error) {
      console.error('Error fetching timeline:', error);
      res.status(500).json({ message: 'Failed to fetch timeline entries' });
    }
  });

  // Get a specific screenshot entry by ID
  app.get('/api/screenshots/:id', async (req, res) => {
    const id = parseInt(req.params.id);
    
    try {
      const entry = await storage.getScreenshotEntry(id);
      
      if (!entry) {
        return res.status(404).json({ message: 'Screenshot not found' });
      }
      
      res.json(entry);
    } catch (error) {
      console.error('Error fetching screenshot:', error);
      res.status(500).json({ message: 'Failed to fetch screenshot' });
    }
  });

  // Search functionality
  app.get('/api/search', async (req, res) => {
    try {
      // Extract and validate search filters
      const rawFilters: Record<string, any> = {
        query: req.query.query,
        date: req.query.date,
        time: req.query.time,
        title: req.query.title,
        url: req.query.url,
        page: req.query.page ? parseInt(req.query.page as string) : undefined,
        limit: req.query.limit ? parseInt(req.query.limit as string) : undefined
      };
      
      // Remove undefined values
      Object.keys(rawFilters).forEach(key => 
        rawFilters[key] === undefined && delete rawFilters[key]
      );
      
      // Validate with zod schema
      const filters = searchFiltersSchema.parse(rawFilters);
      
      // Search entries using storage
      const result = await storage.searchEntries(filters);
      res.json(result);
      
    } catch (error) {
      console.error('Error searching:', error);
      if (error instanceof ZodError) {
        return res.status(400).json({ message: 'Invalid search parameters', errors: error.errors });
      }
      res.status(500).json({ message: 'Failed to search entries' });
    }
  });

  // Get capture status
  app.get('/api/capture/status', async (req, res) => {
    try {
      const status = await storage.getCaptureStatus();
      res.json(status);
    } catch (error) {
      console.error('Error fetching capture status:', error);
      res.status(500).json({ message: 'Failed to fetch capture status' });
    }
  });

  // Toggle capture
  app.post('/api/capture/toggle', async (req, res) => {
    try {
      const status = await storage.toggleCaptureStatus();
      res.json(status);
    } catch (error) {
      console.error('Error toggling capture:', error);
      res.status(500).json({ message: 'Failed to toggle capture' });
    }
  });

  // Sample data generator for testing
  // This endpoint adds some sample entries to the database for demo purposes
  app.post('/api/sample-data', async (req, res) => {
    try {
      // Mock entries that we'll convert to DB entries (only for demo purposes)
      const mockEntries = [
        {
          timestamp: new Date(Date.now() - 1800000),
          title: "Code editor - Python Script",
          app_name: "Visual Studio Code",
          window_title: "screenshot.py - Eidon",
          url: null,
          extracted_text: `import numpy as np\nimport logging\nimport sys\nfrom functools import lru_cache # For caching embeddings and tokenizations`,
          image_path: "https://images.unsplash.com/photo-1587620962725-abab7fe55159?auto=format&fit=crop&w=1200&h=800"
        },
        {
          timestamp: new Date(Date.now() - 3600000),
          title: "Python 3.11 Documentation - Natural Language Processing",
          app_name: "Safari",
          window_title: "Python 3.11 Documentation",
          url: "docs.python.org/3.11/library/nlp.html",
          extracted_text: "Natural Language Processing module provides functions for text processing and analysis. The module includes tokenization, embedding generation...",
          image_path: "https://images.unsplash.com/photo-1603468620905-8de7d86b781e?auto=format&fit=crop&w=1200&h=800"
        },
        {
          timestamp: new Date(Date.now() - 5400000),
          title: "Terminal - PyObjC Installation",
          app_name: "Terminal",
          window_title: "Terminal - bash",
          url: null,
          extracted_text: "$ pip install pyobjc-framework-Vision pyobjc-framework-Quartz python-dateutil\nSuccessfully installed pyobjc-framework-Vision-9.2 pyobjc-framework-Quartz-9.2",
          image_path: "https://images.unsplash.com/photo-1629654297299-c8506221ca97?auto=format&fit=crop&w=1200&h=800"
        }
      ];
      
      // Insert sample data into the database
      const { db } = await import('./db');
      const { screenshotEntries } = await import('@shared/schema');
      
      // Insert each entry individually
      for (const entry of mockEntries) {
        await db.insert(screenshotEntries).values(entry);
      }
      
      res.json({ success: true, message: 'Sample data added successfully' });
      
    } catch (error) {
      console.error('Error adding sample data:', error);
      res.status(500).json({ message: 'Failed to add sample data' });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
