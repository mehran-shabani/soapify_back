import { TestSession, TestResult, TestStatistics, AudioRecording } from '../types';
import { calculateStatistics, formatDuration, formatDateTime, formatFileSize } from '../utils/helpers';

export interface DetailedReport {
  session: TestSession;
  statistics: TestStatistics;
  summary: ReportSummary;
  categoryBreakdown: CategoryBreakdown[];
  errorAnalysis: ErrorAnalysis;
  performanceInsights: PerformanceInsights;
  audioSummary?: AudioSummary;
  recommendations: string[];
  generatedAt: Date;
}

export interface ReportSummary {
  totalEndpoints: number;
  successfulRequests: number;
  failedRequests: number;
  averageResponseTime: number;
  totalTestDuration: number;
  topPerformingCategory: string;
  worstPerformingCategory: string;
  criticalIssues: number;
  warningIssues: number;
}

export interface CategoryBreakdown {
  category: string;
  totalEndpoints: number;
  successCount: number;
  failureCount: number;
  averageResponseTime: number;
  successRate: number;
  criticalEndpoints: string[];
  topIssues: string[];
}

export interface ErrorAnalysis {
  totalErrors: number;
  errorsByType: Record<string, number>;
  errorsByCategory: Record<string, number>;
  criticalErrors: TestResult[];
  commonErrorPatterns: string[];
  suggestedFixes: Record<string, string>;
}

export interface PerformanceInsights {
  fastestEndpoint: { name: string; time: number };
  slowestEndpoint: { name: string; time: number };
  performanceTrends: PerformanceTrend[];
  bottlenecks: string[];
  optimizationSuggestions: string[];
}

export interface PerformanceTrend {
  category: string;
  trend: 'improving' | 'degrading' | 'stable';
  changePercentage: number;
}

export interface AudioSummary {
  totalRecordings: number;
  totalDuration: number;
  averageRecordingLength: number;
  totalSize: number;
  recordingQuality: 'excellent' | 'good' | 'fair' | 'poor';
  recordingsLinkedToSessions: number;
}

export class ReportService {
  private static readonly SLOW_RESPONSE_THRESHOLD = 5000; // 5 seconds
  private static readonly VERY_SLOW_RESPONSE_THRESHOLD = 10000; // 10 seconds
  private static readonly LOW_SUCCESS_RATE_THRESHOLD = 80; // 80%

  static generateDetailedReport(
    session: TestSession, 
    audioRecordings?: AudioRecording[]
  ): DetailedReport {
    const statistics = calculateStatistics(session.results);
    const summary = this.generateSummary(session, statistics);
    const categoryBreakdown = this.generateCategoryBreakdown(session.results);
    const errorAnalysis = this.generateErrorAnalysis(session.results);
    const performanceInsights = this.generatePerformanceInsights(session.results);
    const audioSummary = audioRecordings ? this.generateAudioSummary(audioRecordings, session.id) : undefined;
    const recommendations = this.generateRecommendations(statistics, errorAnalysis, performanceInsights);

    return {
      session,
      statistics,
      summary,
      categoryBreakdown,
      errorAnalysis,
      performanceInsights,
      audioSummary,
      recommendations,
      generatedAt: new Date()
    };
  }

  private static generateSummary(session: TestSession, stats: TestStatistics): ReportSummary {
    const categoryStats = Object.entries(stats.categoriesStats);
    const topPerforming = categoryStats.reduce((best, [category, data]) => 
      data.averageTime < best[1].averageTime ? [category, data] : best
    );
    const worstPerforming = categoryStats.reduce((worst, [category, data]) => 
      data.averageTime > worst[1].averageTime ? [category, data] : worst
    );

    const criticalIssues = session.results.filter(r => 
      r.status === 'error' || r.totalTime > this.VERY_SLOW_RESPONSE_THRESHOLD
    ).length;

    const warningIssues = session.results.filter(r => 
      r.status === 'timeout' || 
      (r.totalTime > this.SLOW_RESPONSE_THRESHOLD && r.totalTime <= this.VERY_SLOW_RESPONSE_THRESHOLD) ||
      (r.accuracyPercentage !== undefined && r.accuracyPercentage < 90)
    ).length;

    const testDuration = session.endTime ? 
      session.endTime.getTime() - session.startTime.getTime() : 
      Date.now() - session.startTime.getTime();

    return {
      totalEndpoints: stats.totalRequests,
      successfulRequests: Math.round(stats.totalRequests * (stats.successRate / 100)),
      failedRequests: Math.round(stats.totalRequests * (stats.errorRate / 100)),
      averageResponseTime: stats.averageResponseTime,
      totalTestDuration: testDuration,
      topPerformingCategory: topPerforming[0],
      worstPerformingCategory: worstPerforming[0],
      criticalIssues,
      warningIssues
    };
  }

  private static generateCategoryBreakdown(results: TestResult[]): CategoryBreakdown[] {
    const categoryMap = new Map<string, TestResult[]>();
    
    results.forEach(result => {
      const category = result.endpoint.category;
      if (!categoryMap.has(category)) {
        categoryMap.set(category, []);
      }
      categoryMap.get(category)!.push(result);
    });

    return Array.from(categoryMap.entries()).map(([category, categoryResults]) => {
      const successCount = categoryResults.filter(r => r.status === 'success').length;
      const failureCount = categoryResults.length - successCount;
      const averageResponseTime = categoryResults.reduce((sum, r) => sum + r.totalTime, 0) / categoryResults.length;
      const successRate = (successCount / categoryResults.length) * 100;

      const criticalEndpoints = categoryResults
        .filter(r => r.status === 'error' || r.totalTime > this.VERY_SLOW_RESPONSE_THRESHOLD)
        .map(r => r.endpoint.name);

      const topIssues = this.identifyTopIssues(categoryResults);

      return {
        category,
        totalEndpoints: categoryResults.length,
        successCount,
        failureCount,
        averageResponseTime,
        successRate,
        criticalEndpoints,
        topIssues
      };
    }).sort((a, b) => b.totalEndpoints - a.totalEndpoints);
  }

  private static generateErrorAnalysis(results: TestResult[]): ErrorAnalysis {
    const errors = results.filter(r => r.status !== 'success');
    
    const errorsByType: Record<string, number> = {};
    const errorsByCategory: Record<string, number> = {};
    const criticalErrors: TestResult[] = [];
    
    errors.forEach(error => {
      // Count by status type
      errorsByType[error.status] = (errorsByType[error.status] || 0) + 1;
      
      // Count by category
      const category = error.endpoint.category;
      errorsByCategory[category] = (errorsByCategory[category] || 0) + 1;
      
      // Identify critical errors
      if (error.status === 'error' || error.totalTime > this.VERY_SLOW_RESPONSE_THRESHOLD) {
        criticalErrors.push(error);
      }
    });

    const commonErrorPatterns = this.identifyErrorPatterns(errors);
    const suggestedFixes = this.generateErrorFixes(errorsByType);

    return {
      totalErrors: errors.length,
      errorsByType,
      errorsByCategory,
      criticalErrors: criticalErrors.slice(0, 10), // Top 10 critical errors
      commonErrorPatterns,
      suggestedFixes
    };
  }

  private static generatePerformanceInsights(results: TestResult[]): PerformanceInsights {
    const successfulResults = results.filter(r => r.status === 'success');
    
    let fastestEndpoint = { name: '', time: Infinity };
    let slowestEndpoint = { name: '', time: 0 };
    
    successfulResults.forEach(result => {
      if (result.totalTime < fastestEndpoint.time) {
        fastestEndpoint = { name: result.endpoint.name, time: result.totalTime };
      }
      if (result.totalTime > slowestEndpoint.time) {
        slowestEndpoint = { name: result.endpoint.name, time: result.totalTime };
      }
    });

    const bottlenecks = this.identifyBottlenecks(results);
    const optimizationSuggestions = this.generateOptimizationSuggestions(results);

    return {
      fastestEndpoint,
      slowestEndpoint,
      performanceTrends: [], // Would require historical data
      bottlenecks,
      optimizationSuggestions
    };
  }

  private static generateAudioSummary(recordings: AudioRecording[], sessionId: string): AudioSummary {
    const sessionRecordings = recordings.filter(r => r.sessionId === sessionId);
    
    const totalDuration = sessionRecordings.reduce((sum, r) => sum + (r.duration || 0), 0);
    const totalSize = sessionRecordings.reduce((sum, r) => sum + (r.size || 0), 0);
    const averageLength = sessionRecordings.length > 0 ? totalDuration / sessionRecordings.length : 0;
    
    // Determine quality based on duration and size
    let quality: 'excellent' | 'good' | 'fair' | 'poor' = 'good';
    if (averageLength > 300000 && totalSize > 10000000) quality = 'excellent'; // 5+ min, 10+ MB
    else if (averageLength > 60000 && totalSize > 2000000) quality = 'good'; // 1+ min, 2+ MB
    else if (averageLength > 10000) quality = 'fair'; // 10+ seconds
    else quality = 'poor';

    return {
      totalRecordings: sessionRecordings.length,
      totalDuration,
      averageRecordingLength: averageLength,
      totalSize,
      recordingQuality: quality,
      recordingsLinkedToSessions: sessionRecordings.length
    };
  }

  private static generateRecommendations(
    stats: TestStatistics, 
    errors: ErrorAnalysis, 
    performance: PerformanceInsights
  ): string[] {
    const recommendations: string[] = [];

    // Success rate recommendations
    if (stats.successRate < this.LOW_SUCCESS_RATE_THRESHOLD) {
      recommendations.push(
        `Success rate is ${stats.successRate.toFixed(1)}%. Consider investigating the ${errors.totalErrors} failed requests to improve reliability.`
      );
    }

    // Performance recommendations
    if (stats.averageResponseTime > this.SLOW_RESPONSE_THRESHOLD) {
      recommendations.push(
        `Average response time is ${formatDuration(stats.averageResponseTime)}. Consider optimizing API endpoints or server infrastructure.`
      );
    }

    // Error-specific recommendations
    if (errors.errorsByType['timeout']) {
      recommendations.push(
        `${errors.errorsByType['timeout']} timeout errors detected. Consider increasing timeout values or optimizing slow endpoints.`
      );
    }

    if (errors.errorsByType['error']) {
      recommendations.push(
        `${errors.errorsByType['error']} server errors detected. Review server logs and error handling implementation.`
      );
    }

    // Category-specific recommendations
    const worstCategory = Object.entries(stats.categoriesStats)
      .sort((a, b) => b[1].averageTime - a[1].averageTime)[0];
    
    if (worstCategory && worstCategory[1].averageTime > this.SLOW_RESPONSE_THRESHOLD) {
      recommendations.push(
        `${worstCategory[0]} category has the slowest average response time (${formatDuration(worstCategory[1].averageTime)}). Focus optimization efforts here.`
      );
    }

    // Throughput recommendations
    if (stats.throughput < 1) {
      recommendations.push(
        `Low throughput detected (${stats.throughput.toFixed(2)} req/sec). Consider implementing connection pooling or increasing concurrency.`
      );
    }

    // General recommendations
    if (recommendations.length === 0) {
      recommendations.push(
        'Overall performance looks good! Continue monitoring and consider setting up automated testing for regression detection.'
      );
    }

    return recommendations;
  }

  private static identifyTopIssues(results: TestResult[]): string[] {
    const issues: string[] = [];
    
    const errorCount = results.filter(r => r.status === 'error').length;
    const timeoutCount = results.filter(r => r.status === 'timeout').length;
    const slowCount = results.filter(r => r.totalTime > this.SLOW_RESPONSE_THRESHOLD).length;
    
    if (errorCount > 0) issues.push(`${errorCount} server errors`);
    if (timeoutCount > 0) issues.push(`${timeoutCount} timeouts`);
    if (slowCount > 0) issues.push(`${slowCount} slow responses`);
    
    return issues;
  }

  private static identifyErrorPatterns(errors: TestResult[]): string[] {
    const patterns: string[] = [];
    
    // Check for authentication errors
    const authErrors = errors.filter(e => 
      e.statusCode === 401 || e.statusCode === 403 || 
      e.error?.toLowerCase().includes('auth')
    );
    if (authErrors.length > 0) {
      patterns.push(`Authentication issues (${authErrors.length} occurrences)`);
    }

    // Check for network errors
    const networkErrors = errors.filter(e => 
      e.status === 'timeout' || 
      e.error?.toLowerCase().includes('network') ||
      e.error?.toLowerCase().includes('connection')
    );
    if (networkErrors.length > 0) {
      patterns.push(`Network connectivity issues (${networkErrors.length} occurrences)`);
    }

    // Check for server errors
    const serverErrors = errors.filter(e => 
      e.statusCode && e.statusCode >= 500
    );
    if (serverErrors.length > 0) {
      patterns.push(`Server-side errors (${serverErrors.length} occurrences)`);
    }

    return patterns;
  }

  private static generateErrorFixes(errorsByType: Record<string, number>): Record<string, string> {
    const fixes: Record<string, string> = {};
    
    if (errorsByType['timeout']) {
      fixes['timeout'] = 'Increase timeout values in configuration or optimize slow API endpoints';
    }
    
    if (errorsByType['error']) {
      fixes['error'] = 'Review server logs, check API endpoint implementations, and verify request payloads';
    }
    
    return fixes;
  }

  private static identifyBottlenecks(results: TestResult[]): string[] {
    const bottlenecks: string[] = [];
    
    // Identify consistently slow endpoints
    const slowEndpoints = results
      .filter(r => r.totalTime > this.SLOW_RESPONSE_THRESHOLD)
      .reduce((acc, r) => {
        const key = r.endpoint.name;
        acc[key] = (acc[key] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);
    
    Object.entries(slowEndpoints).forEach(([endpoint, count]) => {
      if (count > 1) {
        bottlenecks.push(`${endpoint} (consistently slow, ${count} occurrences)`);
      }
    });

    return bottlenecks;
  }

  private static generateOptimizationSuggestions(results: TestResult[]): string[] {
    const suggestions: string[] = [];
    
    const avgResponseTime = results.reduce((sum, r) => sum + r.totalTime, 0) / results.length;
    
    if (avgResponseTime > this.VERY_SLOW_RESPONSE_THRESHOLD) {
      suggestions.push('Consider implementing caching mechanisms for frequently accessed data');
      suggestions.push('Review database query performance and add appropriate indexes');
      suggestions.push('Implement API response compression');
    } else if (avgResponseTime > this.SLOW_RESPONSE_THRESHOLD) {
      suggestions.push('Optimize API endpoint logic and reduce unnecessary processing');
      suggestions.push('Consider implementing request/response caching');
    }

    // Check for large response sizes
    const largeResponses = results.filter(r => r.responseSize && r.responseSize > 100000); // 100KB
    if (largeResponses.length > 0) {
      suggestions.push('Implement pagination for endpoints returning large datasets');
      suggestions.push('Consider using GraphQL or field selection to reduce response sizes');
    }

    return suggestions;
  }

  // Export methods
  static exportDetailedReportJSON(report: DetailedReport): void {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `detailed_report_${report.session.id}_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  static exportDetailedReportHTML(report: DetailedReport): void {
    const html = this.generateHTMLReport(report);
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `detailed_report_${report.session.id}_${new Date().toISOString().split('T')[0]}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  private static generateHTMLReport(report: DetailedReport): string {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Test Report - ${report.session.name}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 20px; background: #f8fafc; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white; padding: 32px; border-radius: 16px; margin-bottom: 24px; }
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 24px 0; }
        .stat-card { background: #f8fafc; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #4f46e5; }
        .stat-number { font-size: 2rem; font-weight: bold; color: #1a202c; }
        .stat-label { font-size: 0.875rem; color: #64748b; text-transform: uppercase; }
        .success { color: #10b981; }
        .error { color: #ef4444; }
        .warning { color: #f59e0b; }
        table { width: 100%; border-collapse: collapse; margin: 16px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
        th { background: #f8fafc; font-weight: 600; }
        .recommendation { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 16px; margin: 8px 0; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>API Test Report</h1>
            <p>Session: ${report.session.name}</p>
            <p>Generated: ${formatDateTime(report.generatedAt)}</p>
        </div>

        <div class="card">
            <h2>Executive Summary</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">${report.summary.totalEndpoints}</div>
                    <div class="stat-label">Total Endpoints</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number success">${report.statistics.successRate.toFixed(1)}%</div>
                    <div class="stat-label">Success Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${formatDuration(report.summary.averageResponseTime)}</div>
                    <div class="stat-label">Avg Response Time</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number ${report.summary.criticalIssues > 0 ? 'error' : 'success'}">${report.summary.criticalIssues}</div>
                    <div class="stat-label">Critical Issues</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Performance by Category</h2>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Endpoints</th>
                        <th>Success Rate</th>
                        <th>Avg Response Time</th>
                        <th>Issues</th>
                    </tr>
                </thead>
                <tbody>
                    ${report.categoryBreakdown.map(cat => `
                        <tr>
                            <td><strong>${cat.category}</strong></td>
                            <td>${cat.totalEndpoints}</td>
                            <td class="${cat.successRate > 90 ? 'success' : cat.successRate > 70 ? 'warning' : 'error'}">${cat.successRate.toFixed(1)}%</td>
                            <td>${formatDuration(cat.averageResponseTime)}</td>
                            <td>${cat.topIssues.join(', ') || 'None'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>

        ${report.errorAnalysis.totalErrors > 0 ? `
        <div class="card">
            <h2>Error Analysis</h2>
            <p><strong>Total Errors:</strong> ${report.errorAnalysis.totalErrors}</p>
            <h3>Errors by Type</h3>
            <ul>
                ${Object.entries(report.errorAnalysis.errorsByType).map(([type, count]) => 
                    `<li><strong>${type}:</strong> ${count}</li>`
                ).join('')}
            </ul>
            <h3>Common Patterns</h3>
            <ul>
                ${report.errorAnalysis.commonErrorPatterns.map(pattern => 
                    `<li>${pattern}</li>`
                ).join('')}
            </ul>
        </div>
        ` : ''}

        <div class="card">
            <h2>Recommendations</h2>
            ${report.recommendations.map(rec => 
                `<div class="recommendation">${rec}</div>`
            ).join('')}
        </div>

        ${report.audioSummary ? `
        <div class="card">
            <h2>Audio Recording Summary</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">${report.audioSummary.totalRecordings}</div>
                    <div class="stat-label">Total Recordings</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${formatDuration(report.audioSummary.totalDuration)}</div>
                    <div class="stat-label">Total Duration</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${formatFileSize(report.audioSummary.totalSize)}</div>
                    <div class="stat-label">Total Size</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${report.audioSummary.recordingQuality}</div>
                    <div class="stat-label">Quality Rating</div>
                </div>
            </div>
        </div>
        ` : ''}
    </div>
</body>
</html>`;
  }
}

export default ReportService;