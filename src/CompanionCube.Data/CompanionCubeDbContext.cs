using CompanionCube.Core.Models;
using Microsoft.EntityFrameworkCore;

namespace CompanionCube.Data;

public class CompanionCubeDbContext : DbContext
{
    public CompanionCubeDbContext(DbContextOptions<CompanionCubeDbContext> options) : base(options)
    {
    }

    public DbSet<ActivityRecord> ActivityRecords { get; set; }
    public DbSet<GoodDayTemplate> GoodDayTemplates { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<ActivityRecord>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.ApplicationName).HasMaxLength(255);
            entity.Property(e => e.WindowTitle).HasMaxLength(500);
            entity.Property(e => e.InferredTask).HasMaxLength(100);
            entity.Property(e => e.Timestamp).HasColumnType("datetime");
            entity.Property(e => e.CurrentState).HasConversion<string>();
        });

        modelBuilder.Entity<GoodDayTemplate>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.ActivityPattern).HasMaxLength(2000);
            entity.Property(e => e.TimingPattern).HasMaxLength(2000);
            entity.Property(e => e.TransitionPattern).HasMaxLength(2000);
            entity.Property(e => e.Date).HasColumnType("date");
            entity.Ignore(e => e.Activities);
        });

        base.OnModelCreating(modelBuilder);
    }
}