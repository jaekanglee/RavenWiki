package com.ppizil.raven

import android.app.Application
import app.cash.sqldelight.driver.android.AndroidSqliteDriver
import com.ppizil.raven.common.db.RavenDatabase
import com.ppizil.raven.common.presentation.di.initKoin
import org.koin.dsl.module

class RavenApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        
        val appModule = module {
            single { 
                val driver = AndroidSqliteDriver(RavenDatabase.Schema, this@RavenApplication, "raven.db")
                RavenDatabase(driver)
            }
        }
        
        initKoin(appModule)
    }
}
