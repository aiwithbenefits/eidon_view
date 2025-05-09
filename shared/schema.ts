import { pgTable, text, serial, integer, boolean, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

// Main entry schema for screenshots captured by Eidon
export const screenshotEntries = pgTable("screenshot_entries", {
  id: serial("id").primaryKey(),
  timestamp: timestamp("timestamp").notNull(),
  title: text("title"),
  app_name: text("app_name"),
  window_title: text("window_title"),
  url: text("url"),
  extracted_text: text("extracted_text"),
  image_path: text("image_path").notNull(),
  embedding: text("embedding"), // Stored as base64 or JSON string
});

// Define search filters schema
export const searchFiltersSchema = z.object({
  query: z.string().optional(),
  date: z.string().optional(),
  time: z.string().optional(),
  title: z.string().optional(),
  url: z.string().optional(),
  page: z.number().default(1),
  limit: z.number().default(12),
});

// For timeline entries
export const timelineEntriesSchema = z.object({
  entries: z.array(
    z.object({
      id: z.number(),
      timestamp: z.number(),
      title: z.string().nullable(),
      appName: z.string().nullable(),
      windowTitle: z.string().nullable(),
      url: z.string().nullable(),
      extractedText: z.string().nullable(),
      imagePath: z.string(),
    })
  ),
  hasMore: z.boolean(),
  currentDate: z.string(),
});

// For capture status
export const captureStatusSchema = z.object({
  active: z.boolean(),
});

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;
export type SearchFilters = z.infer<typeof searchFiltersSchema>;
export type TimelineEntries = z.infer<typeof timelineEntriesSchema>;
export type CaptureStatus = z.infer<typeof captureStatusSchema>;
export type ScreenshotEntry = z.infer<typeof timelineEntriesSchema>["entries"][0];
