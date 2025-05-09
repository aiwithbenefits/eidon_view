import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import path from "path";
import fs from "fs";
import { exec } from "child_process";

// Mock data for development when actual filesystem access isn't available
const MOCK_DATA = {
  isCaptureActive: true,
  entries: [
    {
      id: 1,
      timestamp: Date.now() - 1800000,
      title: "Code editor - Python Script",
      appName: "Visual Studio Code",
      windowTitle: "screenshot.py - Eidon",
      url: null,
      extractedText: `import numpy as np
import logging
import sys
from functools import lru_cache # For caching embeddings and tokenizations

# --- Platform Check for NLEmbedding ---
# NLEmbedding is macOS-specific (Darwin)
IS_DARWIN = sys.platform == "darwin"

if IS_DARWIN:
    try:
        from NaturalLanguage import NLEmbedding, NLTokenizer, NLTokenUnitWord
        from Foundation import NSMakeRange # Used by NLTokenizer
    except ImportError as e:
        # This can happen if PyObjC or its NaturalLanguage bindings are not installed
        raise RuntimeError(
            f"Failed to import Apple NaturalLanguage frameworks (PyObjC). "
            f"Ensure 'pyobjc-framework-Cocoa' and potentially other 'pyobjc-framework-*' "
            f"are installed. Original error: {e}"
        )`,
      imagePath: "https://images.unsplash.com/photo-1587620962725-abab7fe55159?auto=format&fit=crop&w=1200&h=800"
    },
    {
      id: 2,
      timestamp: Date.now() - 3600000,
      title: "Python 3.11 Documentation - Natural Language Processing",
      appName: "Safari",
      windowTitle: "Python 3.11 Documentation",
      url: "docs.python.org/3.11/library/nlp.html",
      extractedText: "Natural Language Processing module provides functions for text processing and analysis. The module includes tokenization, embedding generation...",
      imagePath: "https://images.unsplash.com/photo-1603468620905-8de7d86b781e?auto=format&fit=crop&w=1200&h=800"
    },
    {
      id: 3,
      timestamp: Date.now() - 5400000,
      title: "Terminal - PyObjC Installation",
      appName: "Terminal",
      windowTitle: "Terminal - bash",
      url: null,
      extractedText: "$ pip install pyobjc-framework-Vision pyobjc-framework-Quartz python-dateutil\nSuccessfully installed pyobjc-framework-Vision-9.2 pyobjc-framework-Quartz-9.2",
      imagePath: "https://images.unsplash.com/photo-1629654297299-c8506221ca97?auto=format&fit=crop&w=1200&h=800"
    }
  ]
};

// Try to connect to existing Eidon process or use mock data if in development 
const isProduction = process.env.NODE_ENV === 'production';

export async function registerRoutes(app: Express): Promise<Server> {
  // API endpoints for Eidon functionality
  
  // Get timeline entries
  app.get('/api/timeline', (req, res) => {
    const date = req.query.date as string || new Date().toISOString().split('T')[0];
    const page = parseInt(req.query.page as string || '1');
    const limit = parseInt(req.query.limit as string || '12');
    
    try {
      // In a real implementation, this would fetch actual data from the Eidon database
      const entries = MOCK_DATA.entries;
      const hasMore = false; // Set based on if there are more entries
      
      res.json({
        entries,
        hasMore,
        currentDate: date
      });
    } catch (error) {
      console.error('Error fetching timeline:', error);
      res.status(500).json({ message: 'Failed to fetch timeline entries' });
    }
  });

  // Get a specific screenshot entry by ID
  app.get('/api/screenshots/:id', (req, res) => {
    const id = parseInt(req.params.id);
    
    try {
      // Find the entry with matching ID
      const entry = MOCK_DATA.entries.find(e => e.id === id);
      
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
  app.get('/api/search', (req, res) => {
    const query = req.query.query as string || '';
    const filters = {
      date: req.query.date as string,
      time: req.query.time as string,
      title: req.query.title as string,
      url: req.query.url as string
    };
    const page = parseInt(req.query.page as string || '1');
    const limit = parseInt(req.query.limit as string || '12');
    
    try {
      // In a real implementation, this would use the query and filters to search the Eidon database
      const filteredEntries = MOCK_DATA.entries.filter(entry => {
        let match = true;
        
        // Apply text search
        if (query) {
          const textContent = [
            entry.title,
            entry.appName,
            entry.windowTitle,
            entry.url,
            entry.extractedText
          ].filter(Boolean).join(' ').toLowerCase();
          
          match = match && textContent.includes(query.toLowerCase());
        }
        
        // Apply filters
        if (filters.title) {
          match = match && entry.title?.toLowerCase().includes(filters.title.toLowerCase()) || false;
        }
        if (filters.url && entry.url) {
          match = match && entry.url.toLowerCase().includes(filters.url.toLowerCase());
        }
        
        // Date and time filters would be applied here in a real implementation
        
        return match;
      });
      
      res.json({
        entries: filteredEntries,
        hasMore: false,
        currentDate: filters.date || new Date().toISOString().split('T')[0]
      });
    } catch (error) {
      console.error('Error searching:', error);
      res.status(500).json({ message: 'Failed to search entries' });
    }
  });

  // Get capture status
  app.get('/api/capture/status', (req, res) => {
    try {
      res.json({ active: MOCK_DATA.isCaptureActive });
    } catch (error) {
      console.error('Error fetching capture status:', error);
      res.status(500).json({ message: 'Failed to fetch capture status' });
    }
  });

  // Toggle capture
  app.post('/api/capture/toggle', (req, res) => {
    try {
      // Toggle the capture status
      MOCK_DATA.isCaptureActive = !MOCK_DATA.isCaptureActive;
      
      // In a real implementation, this would call the Eidon Python functions
      // to pause or resume capture
      
      res.json({ active: MOCK_DATA.isCaptureActive });
    } catch (error) {
      console.error('Error toggling capture:', error);
      res.status(500).json({ message: 'Failed to toggle capture' });
    }
  });

  const httpServer = createServer(app);

  return httpServer;
}
