import { users, screenshotEntries, type User, type InsertUser, type ScreenshotEntry } from "@shared/schema";
import { db } from "./db";
import { eq, desc, sql, like, gt, lt, between, inArray } from "drizzle-orm";
import { SearchFilters } from "@shared/schema";

export interface IStorage {
  // User management
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  
  // Screenshot entries
  getScreenshotEntry(id: number): Promise<ScreenshotEntry | undefined>;
  getTimelineEntries(date?: string, page?: number, limit?: number): Promise<{ entries: ScreenshotEntry[], hasMore: boolean, currentDate: string }>;
  searchEntries(filters: SearchFilters): Promise<{ entries: ScreenshotEntry[], hasMore: boolean, currentDate: string }>;
  getCaptureStatus(): Promise<{ active: boolean }>;
  toggleCaptureStatus(): Promise<{ active: boolean }>;
}

export class DatabaseStorage implements IStorage {
  private captureActive: boolean = true;
  
  // User management
  async getUser(id: number): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.username, username));
    return user;
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const [user] = await db
      .insert(users)
      .values(insertUser)
      .returning();
    return user;
  }
  
  // Screenshot entries
  async getScreenshotEntry(id: number): Promise<ScreenshotEntry | undefined> {
    const [entry] = await db.select().from(screenshotEntries).where(eq(screenshotEntries.id, id));
    if (!entry) return undefined;
    
    return {
      id: entry.id,
      timestamp: entry.timestamp instanceof Date ? entry.timestamp.getTime() : Number(entry.timestamp),
      title: entry.title || null,
      appName: entry.app_name || null,
      windowTitle: entry.window_title || null,
      url: entry.url || null,
      extractedText: entry.extracted_text || null,
      imagePath: entry.image_path
    };
  }
  
  async getTimelineEntries(date?: string, page = 1, limit = 12): Promise<{ entries: ScreenshotEntry[], hasMore: boolean, currentDate: string }> {
    // Default date is today
    const currentDate = date || new Date().toISOString().split('T')[0];
    
    // Set up date range for filtering
    const startDate = new Date(currentDate);
    startDate.setHours(0, 0, 0, 0);
    
    const endDate = new Date(currentDate);
    endDate.setHours(23, 59, 59, 999);
    
    // Get one more item than needed to check if there are more pages
    const entriesQuery = await db.select()
      .from(screenshotEntries)
      .where(
        sql`DATE(timestamp) = DATE(${startDate.toISOString()})`
      )
      .orderBy(desc(screenshotEntries.timestamp))
      .limit(limit + 1)
      .offset((page - 1) * limit);
    
    // Check if there are more entries
    const hasMore = entriesQuery.length > limit;
    const entries = hasMore ? entriesQuery.slice(0, limit) : entriesQuery;
    
    // Transform to client expected format
    return {
      entries: entries.map(entry => ({
        id: entry.id,
        timestamp: entry.timestamp instanceof Date ? entry.timestamp.getTime() : Number(entry.timestamp),
        title: entry.title || null,
        appName: entry.app_name || null,
        windowTitle: entry.window_title || null,
        url: entry.url || null,
        extractedText: entry.extracted_text || null,
        imagePath: entry.image_path
      })),
      hasMore,
      currentDate
    };
  }
  
  async searchEntries(filters: SearchFilters): Promise<{ entries: ScreenshotEntry[], hasMore: boolean, currentDate: string }> {
    const { query, date, time, title, url, page = 1, limit = 12 } = filters;
    
    // Start building the query
    let queryBuilder = db.select().from(screenshotEntries);
    
    // Apply filters one by one
    
    // Text search
    if (query) {
      queryBuilder = queryBuilder.where(
        sql`(
          ${like(screenshotEntries.title, `%${query}%`)} OR
          ${like(screenshotEntries.window_title, `%${query}%`)} OR
          ${like(screenshotEntries.app_name, `%${query}%`)} OR
          ${like(screenshotEntries.url, `%${query}%`)} OR
          ${like(screenshotEntries.extracted_text, `%${query}%`)}
        )`
      );
    }
    
    // Date filter
    if (date) {
      queryBuilder = queryBuilder.where(sql`DATE(timestamp) = DATE(${date})`);
    }
    
    // Time filter (assume time is in HH:MM format)
    if (time) {
      // Check if it's a time range (e.g. "10:00-14:00")
      if (time.includes('-')) {
        const [startTime, endTime] = time.split('-');
        queryBuilder = queryBuilder.where(sql`TIME(timestamp) BETWEEN TIME(${startTime}) AND TIME(${endTime})`);
      } else {
        // Exact time match with some flexibility (+/- 1 minute)
        const timeObj = new Date(`1970-01-01T${time}`);
        const startTime = new Date(timeObj.getTime() - 60000); // 1 minute before
        const endTime = new Date(timeObj.getTime() + 60000);   // 1 minute after
        
        queryBuilder = queryBuilder.where(sql`TIME(timestamp) BETWEEN TIME(${startTime.toISOString().split('T')[1]}) AND TIME(${endTime.toISOString().split('T')[1]})`);
      }
    }
    
    // Title filter
    if (title) {
      queryBuilder = queryBuilder.where(like(screenshotEntries.title, `%${title}%`));
    }
    
    // URL filter
    if (url) {
      queryBuilder = queryBuilder.where(like(screenshotEntries.url, `%${url}%`));
    }
    
    // Finalize query with ordering, pagination
    const entriesQuery = await queryBuilder
      .orderBy(desc(screenshotEntries.timestamp))
      .limit(limit + 1)
      .offset((page - 1) * limit);
    
    // Check if there are more entries
    const hasMore = entriesQuery.length > limit;
    const entries = hasMore ? entriesQuery.slice(0, limit) : entriesQuery;
    
    // Transform to client expected format
    return {
      entries: entries.map(entry => ({
        id: entry.id,
        timestamp: entry.timestamp instanceof Date ? entry.timestamp.getTime() : Number(entry.timestamp),
        title: entry.title || null,
        appName: entry.app_name || null,
        windowTitle: entry.window_title || null,
        url: entry.url || null,
        extractedText: entry.extracted_text || null,
        imagePath: entry.image_path
      })),
      hasMore,
      currentDate: date || new Date().toISOString().split('T')[0]
    };
  }
  
  async getCaptureStatus(): Promise<{ active: boolean }> {
    return { active: this.captureActive };
  }
  
  async toggleCaptureStatus(): Promise<{ active: boolean }> {
    this.captureActive = !this.captureActive;
    return { active: this.captureActive };
  }
}

export const storage = new DatabaseStorage();
